/* ============================================================================
   SPB AI ATLAS — the copilot's deep knowledge of EVERY finish   (SPB-AI 2026-09-30)
   Data: js/spb-ai-atlas-data.js (window.SPB_ATLAS_DATA), made by scripts/ai_atlas/build_atlas.py from RENDERS of every catalogue item (paint + spec, the real engine):
   palette, colour name, brings-own-colour vs takes-the-zone-colour, lightness/saturation/contrast, hue spread, texture fineness, metal/rough/clearcoat
   (mean+std of the spec map), sparkle, shine class, shelf memberships, curated tags, M7 quality, protected/gold flags.

     SpbAIAtlas.load() -> Promise            lazy fetch (once)
     SpbAIAtlas.find(opts) -> rows[]         opts: query, type(finish|base|monolithic|pattern|spec), shelf, colour, own('own'|'takes'), shine, metal, sparkle, texture,
                                             multicolor, tags[], min_quality, exclude[], limit, diverse
     SpbAIAtlas.details(key|name) -> object  the full spec sheet in words
     SpbAIAtlas.browse(shelf?) -> object     the shelf map, or one shelf's best + character
     SpbAIAtlas.compare(keys[]) -> object    side by side
     SpbAIAtlas.primer() -> string           the catalogue map for the system prompt
   ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var DATA = null, LOADING = null, IDX = null, BYKEY = null, BYID = null;
    function BASE() { return window.SPB_ATLAS_BASE || ''; }
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    var STOP = { a: 1, an: 1, the: 1, and: 1, or: 1, of: 1, to: 1, in: 1, on: 1, is: 1, it: 1, for: 1, with: 1, i: 1, my: 1, me: 1, that: 1, this: 1, be: 1, are: 1, like: 1, some: 1, very: 1, look: 1, looks: 1, finish: 1, paint: 1 };
    function stem(w) { return w.length > 4 ? w.replace(/(ing|ed|es|s)$/, '') : w.replace(/s$/, ''); }
    function toks(s) { var o = [], w = norm(s).split(' '); for (var i = 0; i < w.length; i++) { if (w[i].length > 1 && !STOP[w[i]]) o.push(stem(w[i])); } return o; }

    // ------------------------------------------------------------------ colour lexicon (HLS predicates)
    function hexHls(h) {
        var r = parseInt(h.substr(1, 2), 16) / 255, g = parseInt(h.substr(3, 2), 16) / 255, b = parseInt(h.substr(5, 2), 16) / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, s = 0, hh = 0, d = mx - mn;
        if (d > 1e-6) { s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); if (mx === r) hh = ((g - b) / d) + (g < b ? 6 : 0); else if (mx === g) hh = (b - r) / d + 2; else hh = (r - g) / d + 4; hh *= 60; }
        return { h: hh, l: l, s: s };
    }
    var COLOURS = {
        red: function (c) { return c.s > 0.35 && (c.h < 14 || c.h >= 346) && c.l > 0.22 && c.l < 0.75; }, crimson: function (c) { return c.s > 0.35 && (c.h < 14 || c.h >= 340) && c.l < 0.45; },
        maroon: function (c) { return c.s > 0.3 && (c.h < 14 || c.h >= 340) && c.l < 0.30; }, burgundy: function (c) { return c.s > 0.3 && (c.h < 14 || c.h >= 330) && c.l < 0.32; },
        orange: function (c) { return c.s > 0.4 && c.h >= 14 && c.h < 42; }, brown: function (c) { return c.s > 0.2 && c.h >= 14 && c.h < 45 && c.l < 0.38; }, bronze: function (c) { return c.s > 0.25 && c.h >= 18 && c.h < 48 && c.l > 0.25 && c.l < 0.5; }, copper: function (c) { return c.s > 0.3 && c.h >= 12 && c.h < 34 && c.l > 0.3 && c.l < 0.6; },
        yellow: function (c) { return c.s > 0.4 && c.h >= 48 && c.h < 66 && c.l > 0.45; }, gold: function (c) { return c.s > 0.35 && c.h >= 36 && c.h < 62 && c.l > 0.3 && c.l < 0.72; },
        lime: function (c) { return c.s > 0.4 && c.h >= 66 && c.h < 100; }, green: function (c) { return c.s > 0.25 && c.h >= 90 && c.h < 165; }, teal: function (c) { return c.s > 0.3 && c.h >= 160 && c.h < 190; }, cyan: function (c) { return c.s > 0.35 && c.h >= 178 && c.h < 205; }, turquoise: function (c) { return c.s > 0.3 && c.h >= 165 && c.h < 200; },
        blue: function (c) { return c.s > 0.3 && c.h >= 200 && c.h < 255; }, navy: function (c) { return c.s > 0.3 && c.h >= 210 && c.h < 255 && c.l < 0.3; }, indigo: function (c) { return c.s > 0.3 && c.h >= 245 && c.h < 280; },
        purple: function (c) { return c.s > 0.25 && c.h >= 255 && c.h < 305; }, violet: function (c) { return c.s > 0.25 && c.h >= 262 && c.h < 295; }, magenta: function (c) { return c.s > 0.35 && c.h >= 295 && c.h < 335; },
        pink: function (c) { return c.s > 0.3 && ((c.h >= 320 && c.h < 350) || (c.h < 14 && c.l > 0.7)) && c.l > 0.5; },
        black: function (c) { return c.l < 0.13; }, white: function (c) { return c.l > 0.9; }, grey: function (c) { return c.s < 0.14 && c.l > 0.15 && c.l < 0.85; }, silver: function (c) { return c.s < 0.16 && c.l > 0.55 && c.l < 0.9; }, charcoal: function (c) { return c.s < 0.16 && c.l > 0.1 && c.l < 0.3; }
    };
    COLOURS.gray = COLOURS.grey; COLOURS.violet = COLOURS.violet; COLOURS.cream = function (c) { return c.l > 0.8 && c.s > 0.2 && c.h > 35 && c.h < 65; };

    // ------------------------------------------------------------------ shine / metal / texture lexicon
    var SHINE_WORDS = { mirror: ['mirror', 'high gloss'], chrome: ['mirror', 'high gloss'], liquid: ['mirror', 'high gloss'], reflective: ['mirror', 'high gloss'], wet: ['high gloss', 'mirror'], glossy: ['gloss', 'high gloss'], gloss: ['gloss', 'high gloss'], satin: ['satin', 'semi-matte'], matte: ['matte', 'semi-matte'], flat: ['matte', 'semi-matte'], dull: ['matte'], rough: ['matte', 'semi-matte'] };
    var METAL_RANK = { none: 0, low: 1, medium: 2, high: 3, full: 4 };
    var METAL_WORDS = { metallic: 2, metal: 2, chrome: 4, mirror: 3, steel: 3, aluminum: 3, aluminium: 3, titanium: 3, gunmetal: 2 };
    var SPARKLE_WORDS = { flake: 1, glitter: 1, sparkle: 1, sequin: 1, stardust: 1, glitz: 1, shimmer: 1, sparkly: 1 };
    var HOLO_WORDS = { holographic: 1, hologram: 1, rainbow: 1, iridescent: 1, prismatic: 1, prism: 1, dichroic: 1, chameleon: 1, colorshift: 1, flip: 1, opal: 1, spectral: 1, oil: 1 };
    var TEX_WORDS = { smooth: 'flat', plain: 'flat', solid: 'flat', fine: 'fine', coarse: 'broad', broad: 'broad', large: 'broad', micro: 'micro', grainy: 'fine', textured: 'medium' };

    var TAGSYN = { camouflage: 'camo', camo: 'camo', rusty: 'rust', rusted: 'rust', corroded: 'rust', patina: 'rust', dirty: 'weathered', worn: 'weathered', old: 'weathered', aged: 'weathered', scratched: 'weathered', distressed: 'weathered', grungy: 'weathered', muddy: 'weathered', weathering: 'weathered',
        glittery: 'glitter', sparkly: 'sparkle', sparkling: 'sparkle', sequins: 'glitter', holo: 'holographic', hologram: 'holographic', chameleon: 'holographic', iridescence: 'iridescent', shifting: 'holographic', snakeskin: 'scales', reptile: 'scales', dragon: 'scales', lizard: 'scales',
        marble: 'stone', granite: 'stone', concrete: 'stone', fiber: 'carbon', fibre: 'carbon', kevlar: 'carbon', mesh: 'weave', knit: 'weave', fabric: 'weave', denim: 'weave', wood: 'wood', timber: 'wood', leather: 'leather', lava: 'flames', fire: 'flames', flame: 'flames', inferno: 'flames',
        galaxy: 'cosmic', nebula: 'cosmic', space: 'cosmic', stars: 'cosmic', cyberpunk: 'cyber', futuristic: 'cyber', tech: 'cyber', luxurious: 'luxury', expensive: 'luxury', fancy: 'luxury', vintage: 'retro', classic: 'retro', stealthy: 'tactical', military: 'tactical', army: 'tactical', ocean: 'water', sea: 'water', ice: 'water', frozen: 'water',
        hex: 'geometric', hexagon: 'geometric', triangles: 'geometric', diamonds: 'geometric', stripes: 'stripes', striped: 'stripes', pinstripe: 'stripes', neon: 'neon', glowing: 'neon', glow: 'neon', spooky: 'spooky', skull: 'spooky', gothic: 'spooky' };
    var TAGSET = {};
    // ------------------------------------------------------------------ load + index
    function load() {
        if (DATA) return Promise.resolve(DATA);
        if (window.SPB_ATLAS_DATA) return Promise.resolve(install(window.SPB_ATLAS_DATA));
        if (LOADING) return LOADING;
        LOADING = new Promise(function (resolve) {
            var sc = document.createElement('script'); sc.async = true; sc.src = BASE() + 'js/spb-ai-atlas-data.js?v=' + (window.SPB_ATLAS_V || '20261004fc2');
            sc.onload = function () { try { resolve(window.SPB_ATLAS_DATA ? install(window.SPB_ATLAS_DATA) : null); } catch (e) { try { console.warn('[AI ATLAS]', e); } catch (x) {} resolve(null); } };
            sc.onerror = function () { LOADING = null; try { console.warn('[AI ATLAS] could not load the data file'); } catch (x) {} resolve(null); };
            document.head.appendChild(sc);
        });
        return LOADING;
    }
    function install(d) {
        DATA = d; BYKEY = {}; BYID = {}; var inv = {}, n = 0;
        d.items.forEach(function (it, i) {
            it._i = i; BYKEY[it.k] = it;
            var id = it.k.replace(/^[a-z]+::/, ''); (BYID[id] = BYID[id] || []).push(it);
            it._type = it.k.split('::')[0];
            it._cols = (it.c || []).map(function (h) { return /^#[0-9a-f]{6}$/i.test(h) ? hexHls(h) : null; });
            var doc = {};
            function add(words, w) { words.forEach(function (t) { doc[t] = (doc[t] || 0) + w; }); }
            add(toks(it.n), 3); add(toks((it.t || []).join(' ')), 2); add(toks(it.d), 1); add(toks((it.s || []).map(function (si) { return d.sections[si]; }).join(' ')), 1); if (it.cn) add(toks(it.cn), 1.5); if (it.g) add(toks(it.g), 1.5);
            it._doc = doc; it._len = Object.keys(doc).length || 1; n++;
            Object.keys(doc).forEach(function (t) { (inv[t] = inv[t] || []).push(i); });
        });
        d.items.forEach(function (it) { (it.t || []).forEach(function (t) { TAGSET[t] = (TAGSET[t] || 0) + 1; }); });
        IDX = { inv: inv, N: n };
        return d;
    }
    function ready() { return !!DATA; }
    function idf(t) { var l = IDX.inv[t]; return l ? Math.log(1 + IDX.N / (1 + l.length)) : 0; }

    // ------------------------------------------------------------------ scoring
    function colourScore(it, words) {
        if (!it._cols || !it._cols.length) return 0;
        var best = 0;
        words.forEach(function (w) {
            var f = COLOURS[w]; if (!f) return;
            it._cols.forEach(function (c, i) { if (c && f(c)) best = Math.max(best, i === 0 ? 1 : (i === 1 ? 0.55 : 0.35)); });
            if (it.cn && it.cn.indexOf(w) !== -1) best = Math.max(best, 1);
        });
        return best;
    }
    function hexColourScore(it, hex) {
        if (!it._cols || !it._cols.length) return 0; var t = hexHls(hex), best = 0;
        it._cols.forEach(function (c, i) { if (!c) return; var dh = Math.min(Math.abs(c.h - t.h), 360 - Math.abs(c.h - t.h)) / 180, dl = Math.abs(c.l - t.l), ds = Math.abs(c.s - t.s); var sim = 1 - Math.min(1, dh * (0.4 + t.s) + dl * 0.9 + ds * 0.4); best = Math.max(best, sim * (i === 0 ? 1 : 0.6)); });
        return best;
    }
    function isFinishType(it) { return it._type === 'base' || it._type === 'monolithic'; }
    function typeOk(it, type) {
        if (!type || type === 'any') return true;
        if (type === 'finish') return isFinishType(it);
        return it._type === type;
    }
    function shelfOk(it, shelf) {
        if (!shelf) return true; var s = norm(shelf);
        return (it.s || []).some(function (si) { return norm(DATA.sections[si]).indexOf(s) !== -1; }) || (it.g && norm(it.g).indexOf(s) !== -1);
    }
    // 2026-10-02: 20 catalogue items are named "R1 REJECTED — ..." / "... — R3 DEV" (owner review rounds): they are never offered to a buyer by a search unless include_hidden
    var HIDK = null, HIDK_FOR = null;
    function hiddenKeys() { if (HIDK_FOR !== DATA) { HIDK = {}; ((DATA && DATA.items) || []).forEach(function (it) { if (/\bREJECTED\b|\bR\d+ DEV\b/.test(it.n || '')) HIDK[it.k] = 1; }); HIDK_FOR = DATA; } return HIDK; }
    function find(o) {
        o = o || {};
        if (!DATA) return [];
        var limit = Math.max(1, Math.min(20, o.limit || 8)), q = String(o.query || ''), qt = toks(q), qraw = norm(q).split(' ');
        var colourWords = [], shineWant = null, metalMin = null, sparkle = !!o.sparkle, holo = false, texWant = o.texture || null, wantNeg = {};
        (o.colour ? String(o.colour).toLowerCase().split(/[ ,/]+/) : []).concat(qraw).forEach(function (w) { if (COLOURS[w] && colourWords.indexOf(w) === -1) colourWords.push(w); });
        var hexCol = /^#[0-9a-f]{6}$/i.test(String(o.colour || '')) ? String(o.colour) : null;
        if (o.shine) shineWant = SHINE_WORDS[String(o.shine).toLowerCase()] || [String(o.shine).toLowerCase()];
        if (o.metal) { var mr = METAL_RANK[String(o.metal).toLowerCase()]; if (mr != null) metalMin = mr; }
        qraw.forEach(function (w) {
            if (!shineWant && SHINE_WORDS[w]) shineWant = SHINE_WORDS[w];
            if (metalMin == null && METAL_WORDS[w] != null) metalMin = METAL_WORDS[w];
            if (SPARKLE_WORDS[w]) sparkle = true;
            if (HOLO_WORDS[w]) holo = true;
            if (!texWant && TEX_WORDS[w]) texWant = TEX_WORDS[w];
        });
        if (o.multicolor) holo = true;
        var tagReq = (o.tags || []).map(norm);
        var excl = {}; (o.exclude || []).forEach(function (k) { excl[k] = 1; });
        if (!o.include_hidden) { var hk0 = hiddenKeys(); for (var hk1 in hk0) excl[hk1] = 1; }
        var tagWant = [];
        qraw.forEach(function (w) { var m = TAGSYN[w] || w; if (TAGSET[m] && tagWant.indexOf(m) === -1) tagWant.push(m); else { var m2 = TAGSYN[stem(w)]; if (m2 && TAGSET[m2] && tagWant.indexOf(m2) === -1) tagWant.push(m2); } });
        var cand = {}, terms = qt.filter(function (t) { return IDX.inv[t]; });
        if (tagWant.length) DATA.items.forEach(function (it, i) { if ((it.t || []).some(function (x) { return tagWant.indexOf(x) !== -1; })) cand[i] = 1; });
        terms.forEach(function (t) { var l = IDX.inv[t]; for (var i = 0; i < l.length; i++) cand[l[i]] = 1; });
        var useAll = !terms.length || o.type || o.shelf || colourWords.length || hexCol || shineWant || metalMin != null || sparkle || holo;
        var pool = [];
        if (useAll && (colourWords.length || hexCol || shineWant || metalMin != null || sparkle || holo || !terms.length || o.shelf || o.type)) { for (var z = 0; z < DATA.items.length; z++) cand[z] = 1; }
        Object.keys(cand).forEach(function (k) {
            var it = DATA.items[k]; if (excl[it.k]) return;
            if (!typeOk(it, o.type || 'finish')) return;
            if (o.shelf && !shelfOk(it, o.shelf)) return;
            if (o.own === 'own' && it.o !== 1 && isFinishType(it)) return; if (o.own === 'takes' && it.o === 1 && isFinishType(it)) return;
            if (o.min_quality && (it.q == null || it.q < o.min_quality)) return;
            if (tagReq.length && !tagReq.every(function (t) { return (it.t || []).some(function (x) { return norm(x) === t; }); })) return;
            var s = 0, why = [];
            // text
            var ts = 0; terms.forEach(function (t) { var w = it._doc[t]; if (w) ts += idf(t) * w / (1 + 0.15 * Math.log(1 + it._len)); });
            s += ts;
            // colour (finishes only)
            if (isFinishType(it) && (colourWords.length || hexCol)) {
                var cs = hexCol ? hexColourScore(it, hexCol) : colourScore(it, colourWords);
                if (cs < 0.3 && it.o === 1) return;           // a finish that brings its own palette and has no such colour: drop
                if (cs < 0.3 && it.o === 0) cs = 0.85;         // takes the zone colour: the zone colour can be set to anything, so it fits any colour ask
                s += cs * 5; if (cs >= 0.9) why.push('is ' + (it.cn || 'that colour'));
            }
            if (shineWant && it.shine) { if (shineWant.indexOf(it.shine) !== -1) { s += 3.5; why.push(it.shine); } else if (isFinishType(it)) s -= 2.5; }
            if (metalMin != null && it.metal) { var mrk = METAL_RANK[it.metal]; if (mrk >= metalMin) { s += 2 + (mrk - metalMin) * 0.3; } else s -= 2.5; }
            if (sparkle) { if (it.sk === 1 || (it.t || []).indexOf('sparkle') !== -1 || (it.t || []).indexOf('glitter') !== -1) { s += 3; why.push('sparkle'); } else if (isFinishType(it)) s -= 1.5; }
            if (holo) { if ((it.t || []).indexOf('holographic') !== -1 || (it.t || []).indexOf('rainbow') !== -1 || (it.hs || 0) > 40) { s += 3.5; why.push('colour-shifting'); } else if (isFinishType(it)) s -= 1.5; }
            if (texWant && it.fb) { if (it.fb === texWant) s += 1.5; else if (texWant === 'flat' && it.fb !== 'flat') s -= 1.2; }
            if (tagWant.length) { var tm = 0; tagWant.forEach(function (tw) { if ((it.t || []).indexOf(tw) !== -1) tm++; }); if (tm) { s += 2.5 + Math.min(tm - 1, 2) * 1.5; why.push(tagWant.join('/')); } else if (terms.length === 0) return; }
            // priors
            if (it.q != null) s += (it.q - 50) / 40; if (it.gold) s += 1.2; if (it.top) s += 0.8;
            if (s <= 0 && terms.length) return;
            if (!terms.length && s <= -1) return;
            pool.push({ it: it, s: s, why: why });
        });
        pool.sort(function (a, b) { return b.s - a.s; });
        // diversity: greedy with shelf + name-stem penalties
        var out = [], shelfCount = {}, stemCount = {};
        var diverse = o.diverse !== false;
        var guard = 0;
        while (out.length < limit && pool.length && guard++ < 400) {
            var bestI = -1, bestS = -1e9, scan = Math.min(pool.length, 60);
            for (var i2 = 0; i2 < scan; i2++) {
                var p = pool[i2], pen = 1;
                if (diverse) { var sk = (p.it.s && p.it.s.length) ? p.it.s[0] : 'x', st = norm(p.it.n).split(' ')[0]; pen = Math.pow(0.78, shelfCount[sk] || 0) * Math.pow(0.6, stemCount[st] || 0); }
                var sc = p.s * pen; if (sc > bestS) { bestS = sc; bestI = i2; }
            }
            var pick = pool.splice(bestI, 1)[0]; out.push(pick);
            var sk2 = (pick.it.s && pick.it.s.length) ? pick.it.s[0] : 'x', st2 = norm(pick.it.n).split(' ')[0]; shelfCount[sk2] = (shelfCount[sk2] || 0) + 1; stemCount[st2] = (stemCount[st2] || 0) + 1;
        }
        return out.map(function (p) { return row(p.it, p.why); });
    }

    // ------------------------------------------------------------------ rendering records as words
    function shelves(it) { return (it.s || []).slice(0, 3).map(function (si) { return DATA.sections[si]; }); }
    function lookWords(it) {
        var b = [];
        if (isFinishType(it) && it.cn) b.push(it.o === 1 ? it.cn + (it.c && it.c.length > 1 ? ' (+' + (it.c.length - 1) + ' more colours)' : '') : 'takes the zone colour');
        if (it.shine) b.push(it.shine);
        if (it.metal && it.metal !== 'none') b.push(it.metal + ' metal');
        if (it.sk === 1) b.push('sparkles'); if ((it.hs || 0) > 40 && (it.hc || 0) >= 4) b.push('multicolour');
        if (it.fb && it.fb !== 'flat') b.push(it.fb + ' texture'); else if (it.fb === 'flat' && isFinishType(it)) b.push('smooth');
        return b.join('; ');
    }
    function typeLabel(it) { return { base: 'base material', monolithic: 'complete special look', pattern: 'paint pattern', spec: 'spec pattern' }[it._type] || it._type; }
    function row(it, why) {
        var r = { key: it.k, name: it.n, kind: typeLabel(it), shelf: shelves(it)[0] || it.g || undefined, look: lookWords(it) || undefined, about: (it.d || '').slice(0, 110) };
        if (it._type === 'spec') { r.id = it.k.replace(/^spec::/, ''); r.group = it.g; r.effect = specEffect(it); delete r.key; delete r.look; delete r.shelf; }
        if (it._type === 'pattern') { r.id = it.k.replace(/^pattern::/, ''); delete r.key; r.effect = specEffect(it); delete r.look; }
        if (it.q != null) r.quality = it.q; if (it.gold) r.flag = 'gold standard'; else if (it.top) r.flag = 'featured';
        if (it.o === 0 && isFinishType(it)) r.colour_mode = 'takes the zone colour (set color)'; else if (it.o === 1 && isFinishType(it)) r.colour_mode = "brings its own palette (use color 'finish')";
        return r;
    }
    function specEffect(it) {
        var b = [];
        if (it.cov != null) b.push(it.cov < 25 ? 'sparse marks' : (it.cov > 65 ? 'dense coverage' : 'half-covered'));
        if (it.fb) b.push(it.fb === 'flat' ? 'even' : it.fb + ' scale');
        if (it.an != null && Math.abs(it.an) > 0.35) b.push(it.an > 0 ? 'vertical streaks' : 'horizontal streaks');
        if (it.con != null) b.push(it.con > 60 ? 'strong contrast' : (it.con < 25 ? 'subtle' : 'medium contrast'));
        if (it.ch) b.push('acts on ' + it.ch);
        return b.join(', ');
    }
    function lookup(k) {
        if (!DATA) return null; if (BYKEY[k]) return BYKEY[k];
        var id = String(k).replace(/^[a-z]+::/, ''), a = BYID[id]; if (a && a.length) return a[0];
        var n = norm(k), best = null;
        for (var i = 0; i < DATA.items.length; i++) { if (norm(DATA.items[i].n) === n) { best = DATA.items[i]; break; } }
        return best;
    }
    function details(k) {
        var it = lookup(k); if (!it) return { error: 'unknown finish ' + k + ' (use find_finishes to get a key)' };
        var o = { key: it.k, name: it.n, kind: typeLabel(it), shelves: shelves(it), about: it.d };
        if (it.lane) o.lane = it.lane;
        if (isFinishType(it)) {
            if (it.c) o.palette = it.c.map(function (h, i) { return h + (i === 0 && it.cn ? ' (' + it.cn + ')' : ''); });
            o.colour_behaviour = it.o === 1 ? "brings its OWN colours; use color 'finish' (a hex tint only shifts it)" : "TAKES the zone colour: set color to '#rrggbb' or 'source' (the paint's own colour)";
            if (it.M) o.spec = { metal: it.M[0] + ' (±' + it.M[1] + ')', roughness: it.R[0] + ' (±' + it.R[1] + ')', clearcoat: it.C[0] + ' (±' + it.C[1] + ')  [16 = max gloss, 255 = none]', reads_as: [it.shine, it.metal + ' metal'].join(', ') };
            o.texture = it.fb || 'unknown'; if (it.sk === 1) o.sparkle = 'yes (' + it.sp + '/100, in the top fifth of the catalogue)'; else if (it.sp >= 15) o.sparkle = 'some fine grain (' + it.sp + '/100)'; if (it.hs > 40) o.colour_spread = 'multi-hue (' + it.hc + ' hue families)'; if (it.V != null) o.contrast = it.V + '/100'; o.lightness = it.L + '/100';
            o.best_for = bestFor(it);
        } else {
            o.effect = specEffect(it); if (it.g) o.group = it.g; if (it.ch) o.default_channels = it.ch; if (it.df) o.defaults = it.df;
        }
        if (it.q != null) o.quality = it.q + '/100' + (it.q >= 80 ? ' (keeper)' : (it.q < 50 ? ' (weak)' : '')); if (it.gold) o.flag = 'gold standard: never altered';
        o.tags = it.t; return o;
    }
    function bestFor(it) {
        var b = [];
        if (it.shine === 'mirror' || it.metal === 'full') b.push('accents, numbers, trim (loud on big areas)');
        if (it.o === 0 && it.shine && (it.shine === 'gloss' || it.shine === 'high gloss')) b.push('body in any colour');
        if (it.shine === 'matte' || it.shine === 'semi-matte') b.push('modern stealth body, contrast next to gloss');
        if (it.sk === 1) b.push('body or accents that should glitter in sunlight');
        if ((it.hs || 0) > 40) b.push('hero panels (loud); keep neighbours calm');
        if (it.V >= 40 && it.fb && it.fb !== 'flat') b.push('graphic panels, hood, sides');
        return b.length ? b : ['general use'];
    }
    function compare(keys) { return { items: (keys || []).slice(0, 6).map(function (k) { var it = lookup(k); if (!it) return { key: k, error: 'unknown' }; var r = row(it); r.palette = it.c; if (it.M) r.spec = { metal: it.M[0], rough: it.R[0], cc: it.C[0] }; r.lightness = it.L; r.contrast = it.V; return r; }) }; }

    // ------------------------------------------------------------------ the shelf map
    function browse(shelf) {
        if (!DATA) return { error: 'the catalogue is still loading; try again' };
        if (!shelf) {
            return { shelves: DATA.sections.map(function (t, i) { return { shelf: t, items: DATA.sectionSize[i], about: (DATA.blurbs && DATA.blurbs[i]) || undefined }; }), note: 'call browse_catalog with a shelf name for its best items, or find_finishes with shelf set' };
        }
        var rows = find({ shelf: shelf, type: 'any', limit: 12, diverse: false, query: '' });
        var idx = -1, s = norm(shelf); DATA.sections.forEach(function (t, i) { if (idx < 0 && norm(t).indexOf(s) !== -1) idx = i; });
        // MCPSCEN 2026-10-05 (MCP run: browse_catalog("candy") returned best: [] with no hint, because no shelf has that name): an unknown shelf now falls back to a
        // word search and says so, with the real shelf names.
        if (idx < 0 || !rows.length) {
            var hits = find({ query: shelf, type: 'any', limit: 12, diverse: true });
            return { shelf: shelf, note: (idx < 0 ? 'no shelf is called "' + shelf + '"' : 'that shelf has no ranked items') + '; these are the best finishes for that word. Shelves: ' + DATA.sections.join(', '), best: hits };
        }
        return { shelf: idx >= 0 ? DATA.sections[idx] : shelf, about: idx >= 0 && DATA.blurbs ? DATA.blurbs[idx] : undefined, best: rows };
    }
    function primer() {
        if (!DATA) return '';
        var lines = [];
        DATA.sections.forEach(function (t, i) { var b = String((DATA.blurbs && DATA.blurbs[i]) || '').split(' | ')[0]; lines.push('- ' + t + ' (' + DATA.sectionSize[i] + '): ' + b.slice(0, 150)); });
        return lines.join('\n');
    }
    window.SpbAIAtlas = { load: load, ready: ready, find: find, details: details, browse: browse, compare: compare, primer: primer, lookup: lookup, _data: function () { return DATA; }, _install: install };
})();
