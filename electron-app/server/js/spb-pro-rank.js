/* ============================================================================
   SPB PRO RANK — scores the WHOLE catalogue for a painter's situation   (owner 2026-10-03: "we aren't even touching the tip of the iceberg")
   Replaces the ~25 hand-picked keys the finish advisor used to rotate through. Everything here reads the atlas (measured) and the cards (LLM-written, see spb-ai-cards.js).

     SpbProRank.search(query, o)  -> [{key, name, s, why[]}]      free-text ("dusty dirt late model") with diversity;  o: limit, offset, types, own, exclude[], seed, novelty
     SpbProRank.suggest(ctx)      -> {rows:[{key,name,s,why[],lane}], total}     situation-aware (part, goal, colours, neighbours, novelty), one LANE at a time
        ctx.lane: 'keep'    shine-only finishes that keep the paint colours (Foundation + takes-the-zone-colour bases)
                  'complete' complete special looks that bring their own palette (ranked by palette HARMONY with the scheme)
                  'texture'  spec patterns (shine texture) and paint patterns to layer on top
        ctx.target {id,thin,readable,all,label}, ctx.goal, ctx.query, ctx.colours {target,body,scheme[]}, ctx.bodyClass, ctx.novelty 0|1|2, ctx.exclude[], ctx.offset, ctx.limit, ctx.seed
   ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    function AT() { return window.SpbAIAtlas; }
    function CD() { return window.SpbAICards; }
    function hls(h) {
        if (!/^#[0-9a-f]{6}$/i.test(String(h || ''))) return null;
        var r = parseInt(h.substr(1, 2), 16) / 255, g = parseInt(h.substr(3, 2), 16) / 255, b = parseInt(h.substr(5, 2), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, s = 0, hh = 0, d = mx - mn;
        if (d > 1e-6) { s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); if (mx === r) hh = ((g - b) / d) + (g < b ? 6 : 0); else if (mx === g) hh = (b - r) / d + 2; else hh = (r - g) / d + 4; hh *= 60; }
        return { h: hh, l: l, s: s };
    }
    function hueDist(a, b) { var d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; }
    function rnd(seed, str) { var h = seed | 0, i; for (i = 0; i < str.length; i++) { h = ((h << 5) - h + str.charCodeAt(i)) | 0; } h = (h ^ (h >>> 13)) * 1274126177; h = h ^ (h >>> 16); return ((h >>> 0) % 10000) / 10000; }
    function family(it) { return it._type + ':' + String(it.n || '').toLowerCase().split(/[ :\-—\/(]/)[0]; }
    function shineClass(it) { var s = it.shine || ''; if (s === 'matte' || s === 'semi-matte') return 'flat'; if (s === 'satin') return 'satin'; return 'glossy'; }

    // ------------------------------------------------------------------ palette harmony of a complete look with the buyer's colours (0..1)
    function harmony(it, scheme) {
        var pal = (it.c || []).map(hls).filter(Boolean), sc = (scheme || []).map(hls).filter(Boolean);
        if (!pal.length || !sc.length) return 0.5;
        var best = 0, i, j;
        for (i = 0; i < Math.min(2, pal.length); i++) {
            var p = pal[i], wgt = i === 0 ? 1 : 0.8;
            for (j = 0; j < sc.length; j++) {
                var q = sc[j], v;
                if (p.s < 0.14 || q.s < 0.12) v = 0.72;                                  // a neutral (grey / black / white / silver) sits with anything
                else { var d = hueDist(p.h, q.h); v = d < 28 ? 0.92 : (d > 150 ? 0.88 : (d > 105 && d <= 135 ? 0.55 : (d >= 28 && d < 50 ? 0.62 : (d >= 50 && d <= 105 ? (p.s > 0.5 && q.s > 0.5 ? 0.12 : 0.3) : 0.4)))); }
                if (Math.abs(p.l - q.l) > 0.3) v += 0.06;
                best = Math.max(best, v * wgt);
            }
        }
        return Math.min(1, best);
    }

    // ------------------------------------------------------------------ goals: words that find them + the card facets they want
    var GOALS = {
        pop: { q: 'bold bright vivid glow contrast eye-catching', loud: 4, busy: 3, moods: ['aggressive', 'fiery', 'playful', 'wild'] },
        premium: { q: 'luxury premium elegant refined rich', loud: 2, busy: 2, moods: ['luxury', 'elegant'] },
        shimmer: { q: 'shimmer sparkle pearl fine flake', loud: 3, busy: 2, moods: ['luxury', 'elegant', 'dreamy'] },
        deep: { q: 'deep rich candy glossy wet tinted', loud: 3, busy: 2, moods: ['luxury', 'elegant', 'dreamy'] },
        retro: { q: 'retro vintage classic', loud: 2, busy: 2, moods: ['retro'] },
        stealth: { q: 'stealth matte black dark flat', loud: 1, busy: 1, moods: ['stealth', 'industrial'] },
        readable: { q: 'plain flat clean solid', loud: 1, busy: 1, moods: ['clean'] },
        metalbright: { q: 'metallic bright pearl satin metal', loud: 3, busy: 2, moods: ['luxury', 'techy'] },
        subtle: { q: 'subtle calm understated soft', loud: 1, busy: 1, moods: ['clean', 'elegant'] },
        plain: { q: 'plain solid clean simple flat', loud: 1, busy: 1, moods: ['clean'] }
    };

    function has(a, x) { return a.indexOf(x) !== -1; }
    var CANON = { 'base::gloss': 1, 'base::satin': 1, 'base::matte': 1, 'base::wet_look': 1, 'base::semi_gloss': 1, 'base::f_metallic': 1, 'base::f_pearl': 1, 'base::f_candy': 1, 'base::f_satin_chrome': 1, 'base::f_chrome': 1, 'base::f_brushed': 1, 'base::f_satin_pearl': 1, 'base::f_matte_metallic': 1, 'base::f_dark_chrome': 1, 'base::f_carbon_fiber': 1, 'base::flat_black': 1, 'base::gunmetal': 1, 'base::cerakote': 1, 'base::metallic': 1, 'base::pearl': 1, 'base::candy': 1, 'base::chrome': 1 };
    var CANON_DARK = { 'base::gunmetal': 1, 'base::cerakote': 1, 'base::flat_black': 1 };
    var FNDIDX = -2;
    function isFoundation(at, it) {
        if (FNDIDX === -2) { FNDIDX = -1; var d = at._data(); for (var i = 0; i < d.sections.length; i++) { if (d.sections[i] === 'Foundation') FNDIDX = i; } }
        return FNDIDX >= 0 && (it.s || []).indexOf(FNDIDX) !== -1 && it._type === 'base' && it.o === 0;
    }
    function typeOf(it) { return it._type; }

    // ------------------------------------------------------------------ candidate pool for a lane
    var HID_RE = /\bREJECTED\b|\bR\d+ DEV\b/;      // owner review rounds ("R1 REJECTED — ...", "... — R3 DEV"): never suggested
    function laneOk(it, lane, specOnly) {
        var t = it._type; if (HID_RE.test(it.n || '')) return false;
        if (lane === 'keep') return (t === 'base' || t === 'monolithic') && it.o === 0;
        if (lane === 'complete') return (t === 'base' || t === 'monolithic') && it.o === 1;
        if (lane === 'texture') return t === 'spec' || (t === 'pattern' && !specOnly);
        return t === 'base' || t === 'monolithic';
    }

    function suggest(ctx) {
        ctx = ctx || {}; var a = AT(), c = CD(); if (!a || !a.ready() || !c || !c.ready()) return { rows: [], total: 0 };
        var lane = ctx.lane || 'any', goal = GOALS[ctx.goal] || null, tg = ctx.target || null, col = ctx.colours || {}, scheme = [col.target, col.body].concat(col.scheme || []).filter(Boolean);
        var nov = ctx.novelty == null ? 1 : ctx.novelty, excl = {}, seed = ctx.seed || 1;
        (ctx.exclude || []).forEach(function (k) { excl[k] = 1; });
        if (ctx.avoid && ctx.avoid.length) { var avs = avoidSet(ctx.avoid); for (var ak in avs) excl[ak] = 1; }
        var qtxt = String(ctx.query || '').trim();
        var classic = !qtxt;      // no descriptive words: the painter wants sensible, proven choices (mood / era / class still steer the ranking)
        if (ctx.classic != null) classic = !!ctx.classic;
        // retrieval: the ask / goal words over the cards (BM25) ; with no words at all every item of the lane is a candidate
        var cand = {}, maxS = 1, keys = [], n;
        if (qtxt) {
            var typ = lane === 'texture' ? (ctx.specOnly ? ['spec'] : ['spec', 'pattern']) : ['base', 'monolithic'];
            var rs = c.search(qtxt, { types: typ, limit: 1200 });
            rs.forEach(function (r) { var it = a.lookup(r.key); if (it && laneOk(it, lane, ctx.specOnly) && !excl[r.key]) { cand[r.key] = r.s; if (r.s > maxS) maxS = r.s; } });
        }
        if (qtxt && ctx.classic == null) {
            var topHits = 0, lexHit = false, LX = c._lex || {}; qtxt.split(' ').forEach(function (wd) { if (LX[wd] || LX[c.toks(wd)[0]]) lexHit = true; });
            c.search(qtxt, { types: lane === 'texture' ? ['spec', 'pattern'] : ['base', 'monolithic'], limit: 1 }).forEach(function (r) { topHits = Math.max(topHits, r.hits.length); });
            if (topHits < 3 && !lexHit) classic = true;                     // loose words ("night", "black", "lit") describe a situation, not a look: stay with the proven choices
        }
        if (!qtxt || Object.keys(cand).length < 60) {                         // (the pool of the lane is ranked by role, goal, harmony and quality)                          // thin retrieval: widen to the whole lane so there is always something to rank
            var d = a._data(); for (n = 0; n < d.items.length; n++) { var it0 = d.items[n]; if (laneOk(it0, lane, ctx.specOnly) && !excl[it0.k] && cand[it0.k] == null) cand[it0.k] = 0; }
        }
        if (ctx.only) { var oc = {}; ctx.only.forEach(function (k) { if (a.lookup(k) && c.card(k)) oc[k] = cand[k] != null ? cand[k] : 0; }); cand = oc; classic = false; }      // rank exactly these (no pool, no diversity)
        var rows = [];
        Object.keys(cand).forEach(function (k) {
            var it = a.lookup(k), cd = c.card(k); if (!it || !cd) return;
            var s = 0, why = [];
            s += (ctx.qw || CFG.qw) * (cand[k] / maxS);                                // what the words say (CFG.qw / ctx.qw: how much the described words outweigh role, rating and harmony)
            if (classic && lane !== 'texture') {
                var fnd = isFoundation(a, it);
                if (lane === 'keep') {
                    if (it._type !== 'base') return;                                                   // the first pages are the proven BASE materials; takes-colour effects come on "show me more"
                    if (CANON[k] && !(CANON_DARK[k] && !(ctx.goal === 'stealth' || ctx.goal === 'subtle' || ctx.goal === 'readable' || ctx.goal === 'plain' || (tg && tg.readable)))) s += CFG.w.canon;      // the names every painter already knows (familiarity prior); the dark utility looks only when the goal is stealth / quiet
                    s += (fnd ? CFG.w.found : 0) + 1.0 + (it.q != null && it.q >= 70 ? 0.6 : (it.q == null ? -0.2 : -0.8)); if (cd.busy >= 3) s -= 0.8 * (cd.busy - 2);
                    if (cd.loud <= 1 && cd.busy <= 1 && (has(cd.mood, 'industrial') || has(cd.mood, 'stealth')) && !(ctx.goal === 'stealth' || ctx.goal === 'readable' || ctx.goal === 'subtle' || (tg && tg.readable))) s -= 1.2;      // utility looks (primer, powder coat) make a dull first suggestion
                }
                else { if (cd.loud > 3 || cd.busy > 3) s -= 1.6; if (nov < 2 && (has(cd.mood, 'wild') || has(cd.mood, 'spooky') || has(cd.mood, 'cosmic') || has(cd.mood, 'playful'))) s -= 1.4; if (it.q != null && it.q >= 70) s += 0.5; }
            }
            // role fit
            if (tg && tg.readable) { var plain = (cd.busy <= 1 && cd.loud <= 2 && it.sk !== 1 && it.shine !== 'mirror' && it.metal !== 'full'); s += plain ? 1.6 : -2.2; if (plain) why.push('plain enough to keep digits crisp'); }
            else if (tg && tg.thin) { s += (cd.busy <= 2 ? 0.9 : (cd.busy >= 4 ? -1.0 : 0)); if (has(cd.use, 'stripes') || has(cd.use, 'trim')) { s += 0.5; why.push('made for accents and trim'); } }
            else if (tg && !tg.all) { var up = (tg.id === 'hood' || tg.id === 'roof' || tg.id === 'sides' || tg.id === 'trunk') && has(cd.use, tg.id); if (up) { s += 0.5; why.push('suits the ' + tg.id); } if (cd.busy >= 5) s -= 0.4; }
            else { if (has(cd.use, 'body')) s += 0.3; if (cd.loud >= 5) s -= 0.5; }
            // RATED usefulness (rated once by an LLM from the picture + numbers, see scripts/ai_atlas/rate_cards.py): overall appeal and risk, then the fit for THIS role
            s += CFG.w.appeal * (cd.appeal - 3) - CFG.w.risk * (cd.risk - 2.5);
            if (tg && tg.readable) s += 0.4 * (cd.accent - 3) - 0.5 * (cd.risk - 2);
            else if (tg && tg.thin) s += CFG.w.accent * (cd.accent - 3);
            else if (tg && !tg.all && tg.id !== 'body') s += CFG.w.hero * ((cd.body + cd.hero) / 2 - 3);
            else s += CFG.w.body * (cd.body - 3);
            // goal fit
            if (goal) {
                s -= CFG.w.loudG * Math.abs(cd.loud - goal.loud); s -= CFG.w.busyG * Math.abs(cd.busy - goal.busy);
                if (ctx.goal === 'pop') { s += (it.metal && it.metal !== 'none' ? 0.55 : 0) + ((it.shine === 'matte' || it.shine === 'semi-matte') ? -0.7 : 0) + (it.sk === 1 ? 0.2 : 0); }      // "pop" = intensity (metal, depth, gloss), not a flatter finish
                var mh = 0; goal.moods.forEach(function (m) { if (has(cd.mood, m)) mh++; }); if (mh) { s += 0.5 * Math.min(2, mh); why.push(cd.mood.slice(0, 2).join(' / ')); }
                // material affinity of the goal (judged 2026-10-03: "a bit of shimmer" must be a visibly shimmering material, "deep" a glossy tinted one)
                var wd = (it.n + ' ' + cd.look + ' ' + cd.syn.slice(0, 10).join(' ')).toLowerCase();
                var affS = s; if (ctx.goal === 'shimmer') { s += ((it.sp != null && it.sp >= 15) ? 0.7 : 0) + (/pearl|flake|shimmer|sparkl|glitter|metallic/.test(wd) ? 0.8 : 0) - (((it.sp || 0) < 5 && it.metal === 'none') ? 0.9 : 0) - (/gunmetal|obsidian|graphite|charcoal|industrial|cerakote/.test(wd) ? CFG.shimmerDown : 0) - (/brushed|wet look/.test(wd) && !(it.sp != null && it.sp >= 15) ? CFG.shimmerDown : 0); }
                else if (ctx.goal === 'pop') { s += (/candy|pearl|nacre|wet look|lacquer|chrome|flake|sparkl|mirror/.test(wd) ? CFG.pop.up : 0) - (/gunmetal|obsidian|graphite|charcoal|brushed|industrial|cerakote|primer|flat black|matte|cover cloth/.test(wd) ? CFG.pop.down : 0); }
                else if (ctx.goal === 'readable' && !(tg && tg.readable)) { s += (/gunmetal|graphite|cerakote|brushed|obsidian|industrial|carbon/.test(wd) ? -CFG.readDown : 0) + ((it.shine === 'gloss' || it.shine === 'high gloss') && it.metal === 'none' ? 0.4 : 0) - ((it.shine === 'matte' || it.shine === 'semi-matte') ? CFG.readMatte : 0); }
                else if (ctx.goal === 'deep') { s += ((it.shine === 'high gloss' || it.shine === 'mirror') ? 0.4 : 0) + (/candy|deep|wet|tinted|lacquer/.test(wd) ? 0.9 : 0) - (it.shine === 'matte' ? 0.8 : 0); }
                else if (ctx.goal === 'premium') { s += (/pearl|candy|nacre|brushed|ceramic|satin metal|metallic/.test(wd) ? 0.6 : 0); }
                else if (ctx.goal === 'stealth') { s += ((it.shine === 'matte' || it.shine === 'semi-matte') ? 0.7 : 0) - (it.shine === 'mirror' ? 1.0 : 0); }
                if ((ctx.goal === 'retro' || ctx.goal === 'deep' || ctx.goal === 'pop' || ctx.goal === 'shimmer') && CANON_DARK[k]) s -= CFG.darkUtil;      // 2026-10-02 scenario judge: Gunmetal / Cerakote / Flat Black are poor answers for retro / deep / pop / shimmer (0.0-0.6 of 2)
                s = affS + (s - affS) * CFG.w.aff;
            }
            if (ctx.mood && ctx.mood.length) { var mm = 0; ctx.mood.forEach(function (m) { if (has(cd.mood, m)) mm++; }); s += 0.8 * mm; }
            if (ctx.era && ctx.era.length) { var em = 0; ctx.era.forEach(function (m) { if (has(cd.era, m)) em++; }); s += 0.8 * em; }
            if (ctx.fit && ctx.fit.length) { var fm = 0; ctx.fit.forEach(function (m) { if (has(cd.fit, m)) fm++; }); s += 0.4 * fm; }
            // neighbours: a difference in shine reads (thin accents) ; a metal-on-colour caution
            if (tg && tg.thin && ctx.bodyClass && it._type !== 'spec' && it._type !== 'pattern') { if (shineClass(it) !== ctx.bodyClass) { s += 0.7; why.push('a different shine from the body'); } }
            if (it.o === 0 && it.metal === 'full' && col.target && hls(col.target) && hls(col.target).s > 0.2 && hls(col.target).l < 0.75) s -= 0.9;
            // complete looks: palette harmony with the scheme
            if (lane === 'complete' || (lane === 'any' && it.o === 1)) { var hm = harmony(it, scheme); s += CFG.w.harm * (hm - 0.5) + 0.3 * (cd.appeal - 3) + (nov < 2 ? 0.3 * (3 - cd.loud) : 0); if (hm >= 0.85) why.push('its palette suits your colours'); else if (hm <= 0.25) why.push('its colours may clash with yours'); }
            // quality prior, novelty dial and a stable jitter so repeated asks differ
            if (it.q != null) s += CFG.w.qual * (it.q - 60) / 60; if (it.gold) s += 0.8;
            if (nov === 0) { s += (cd.loud <= 3 ? 0.5 : -0.5) + (it.q != null && it.q >= 80 ? 0.5 : 0); } else if (nov >= 2) { s += (cd.loud >= 4 ? 0.7 : 0) + (has(cd.mood, 'wild') || has(cd.mood, 'cosmic') ? 0.5 : 0); }
            s += CFG.w.jit * rnd(seed, k);
            rows.push({ key: k, name: it.n, s: s, why: why, lane: lane, it: it, cd: cd });
        });
        rows.sort(function (x, y) { return y.s - x.s; });
        // diversity: greedy MMR over family / hue bucket / mood
        var out = [], famC = {}, hueC = {}, moodC = {}, matC = {}, limit = (ctx.offset || 0) + (ctx.limit || 6), guard = 0, pool = rows.slice(0, 260);
        function mat(it) { return it._type === 'spec' || it._type === 'pattern' ? it._type : (shineClass(it) + '/' + (it.metal || 'none') + (it.sk === 1 ? '/sp' : '')); }
        if (ctx.only) out = rows.slice();
        while (!ctx.only && out.length < limit && pool.length && guard++ < 2000) {
            var bi = 0, bs = -1e9, i;
            for (i = 0; i < Math.min(pool.length, 40); i++) {
                var r = pool[i], f = family(r.it), hb = Math.round(((hls((r.it.c || [])[0]) || { h: 0 }).h) / 40), m0 = (r.cd.mood[0] || '-');
                var sc = r.s * Math.pow(0.55, famC[f] || 0) * Math.pow(0.86, hueC[hb] || 0) * Math.pow(0.9, moodC[m0] || 0) * Math.pow(0.8, matC[mat(r.it)] || 0);
                if (r.s < 0) sc = r.s - 0.8 * ((famC[f] || 0) + (hueC[hb] || 0) * 0.3);
                if (sc > bs) { bs = sc; bi = i; }
            }
            var p = pool.splice(bi, 1)[0]; out.push(p);
            var ff = family(p.it), hh = Math.round(((hls((p.it.c || [])[0]) || { h: 0 }).h) / 40), mm0 = (p.cd.mood[0] || '-'); famC[ff] = (famC[ff] || 0) + 1; hueC[hh] = (hueC[hh] || 0) + 1; moodC[mm0] = (moodC[mm0] || 0) + 1; matC[mat(p.it)] = (matC[mat(p.it)] || 0) + 1;
        }
        var page = out.slice(ctx.offset || 0, limit).map(function (r) { return { key: r.key, name: r.name, s: r.s, why: r.why, lane: lane, look: r.cd.look, loud: r.cd.loud, busy: r.cd.busy, mood: r.cd.mood, use: r.cd.use, pair: r.cd.pair, avoid: r.cd.avoid, analog: r.cd.analog }; });
        return { rows: page, total: rows.length };
    }

    // free-text search with diversity (the advisor's "find" and the AI's find_finishes)
    var CFG = { w: { appeal: 0.45, risk: 0.35, accent: 0.6, body: 0.55, hero: 0.5, qual: 1.0, harm: 3.2, loudG: 0.35, busyG: 0.25, canon: 0.9, found: 0.8, aff: 1.0, jit: 0.5 }, pop: { up: 1.6, down: 1.6 }, shimmerDown: 1.6, darkUtil: 1.2, readDown: 1.4, readMatte: 1.0, wB: 0.7, qw: 3.0, likeSim: 3.0, likeMod: 1.0, likePal: 1.1 };      // like(): similarity weight, modifier multiplier, palette-similarity weight (tuned with scripts/ai_atlas/like_run.js + like_judge.py)

    // ------------------------------------------------------------------ AVOID: "no glitter", "nothing holographic or chameleon", "don't want a wrap look"
    //   a hard exclusion set: measured predicates for the common traits (sparkle, chrome, matte, gloss, metallic ...) UNION the finishes the card search finds for the phrase itself
    var AV_PRED = [
        [/^(?:sparkle|sparkly|sparkles|glitter|glittery|flake|flakes|flaky|shimmer|shimmery|sequin|sequins|glitz|glitzy)$/, function (it, cd) { return (it.sp != null && it.sp >= 40) || it.sk === 1 || /\b(?:sparkle|glitter|flake|shimmer|sequin|crystal dust|diamond dust)\b/.test(cd.look + ' ' + cd.syn.slice(0, 8).join(' ')); }],
        [/^(?:chrome|chromes|mirror)$/, function (it, cd) { return it.shine === 'mirror' || it.metal === 'full' || /chrome/i.test(it.n) || /\bchrome\b/.test(cd.look); }],
        [/^(?:metallic|metal|metals)$/, function (it) { return it.metal === 'medium' || it.metal === 'high' || it.metal === 'full' || /\bmetallic\b/i.test(it.n + ' ' + (it.t || []).join(' ')); }],      // MSR-FIX-A: tags / name too
        [/^(?:matte|matt|flat|dull)$/, function (it) { return it.shine === 'matte' || it.shine === 'semi-matte'; }],
        [/^(?:gloss|glossy|shiny|shine|glare|glaring)$/, function (it) { return it.shine === 'gloss' || it.shine === 'high gloss' || it.shine === 'mirror'; }],
        [/^(?:satin)$/, function (it) { return it.shine === 'satin'; }],
        [/^(?:candy)$/, function (it, cd) { return /candy/i.test(it.n) || /\bcandy\b/.test(cd.look + ' ' + cd.syn.slice(0, 6).join(' ')); }],
        [/^(?:pearl|pearly|pearlescent)$/, function (it, cd) { return /pearl/i.test(it.n + ' ' + (it.t || []).join(' ')) || /\bpearl/.test(cd.look + ' ' + cd.syn.slice(0, 6).join(' ')); }],
        [/^(?:holographic|hologram|holograms|holo|chameleon|iridescent|iridescence|rainbow|prism|prismatic|dichroic|opalescent|colou?r[- ]?shift\w*|colou?r[- ]?flip\w*|flip|flop|oil[- ]?slick|spectral|interference)$/, function (it, cd) { return /holo|chameleon|iridesc|rainbow|prism|dichroic|colou?r.?shift|colou?r.?flip|flip|interference|spectral|oil.?slick|opal/i.test(it.n + ' ' + cd.look + ' ' + cd.syn.slice(0, 10).join(' ') + ' ' + (it.t || []).join(' ')); }],
        [/^(?:neon|glow|glowing|fluorescent|day.?glo)$/, function (it, cd) { return /neon|glow|fluoresc/i.test(it.n + ' ' + cd.look + ' ' + cd.syn.slice(0, 8).join(' ')); }],
        [/^(?:camo|camouflage)$/, function (it, cd) { return /camo/i.test(it.n + ' ' + cd.look + ' ' + cd.syn.slice(0, 8).join(' ') + ' ' + (it.t || []).join(' ')); }],
        [/^(?:carbon)$/, function (it, cd) { return /carbon/i.test(it.n + ' ' + cd.look + ' ' + (it.t || []).join(' ')); }],
        [/^(?:wrap|vinyl)$/, function (it, cd) { return /wrap|vinyl/i.test(it.n + ' ' + cd.look); }],
        [/^(?:flames?|fire|fiery)$/, function (it, cd) { return /flame|fire|fiery|inferno|blaze/i.test(it.n + ' ' + cd.look + ' ' + cd.syn.slice(0, 8).join(' ')); }],
        [/^(?:pattern|patterned|busy|busier|detailed)$/, function (it, cd) { return cd.busy >= 4; }],
        [/^(?:stripes?|checkers?|checkered|plaid)$/, function (it, cd, key) { return new RegExp(key.replace(/s$/, '').replace(/ed$/, ''), 'i').test(it.n + ' ' + cd.look); }]
    ];
    function isTrait(ph) { var toks = String(ph || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean), i, j; for (i = 0; i < toks.length; i++) { for (j = 0; j < AV_PRED.length; j++) { if (AV_PRED[j][0].test(toks[i])) return true; } } return false; }
    var AV_CACHE = {};
    // MSR-FIX-A (2026-10-03): disliked colours ("camo without green") drop items whose OWN name / tags / colour name say that colour (avoidSet only; isTrait unchanged)
    var AV_COL = /^(?:red|orange|yellow|green|blue|purple|violet|pink|black|white|grey|gray|silver|gold|golden|bronze|copper|brown|tan|teal|cyan|magenta|navy|maroon|beige|cream|lime|turquoise)$/;
    function avCol(it, tk) { var k = tk === 'gray' ? 'grey' : (tk === 'golden' ? 'gold' : tk), hay = (String(it.n || '') + ' ' + (it.t || []).join(' ') + ' ' + String(it.cn || '')).toLowerCase(); return new RegExp('\\b' + k + '\\b').test(hay) || (k === 'grey' && /\bgray\b/.test(hay)); }
    function avoidSet(phrases) {
        var out = {}, c = CD(), a = AT(); if (!c || !c.ready() || !a) return out;
        (phrases || []).forEach(function (ph) {
            ph = String(ph || '').toLowerCase().trim(); if (!ph) return;
            if (AV_CACHE[ph]) { for (var k0 in AV_CACHE[ph]) out[k0] = 1; return; }
            var set = {}, toks = ph.split(/[^a-z0-9]+/).filter(Boolean), d = a._data(), i, ti;
            var preds = []; toks.forEach(function (tk) { AV_PRED.forEach(function (pr) { if (pr[0].test(tk)) preds.push([pr[1], tk]); }); if (AV_COL.test(tk) && toks.length <= 3) preds.push([function (it, cd, k) { return avCol(it, k); }, tk]); });
            if (preds.length) { for (i = 0; i < d.items.length; i++) { var it = d.items[i], cd = c.card(it.k); if (!cd) continue; for (ti = 0; ti < preds.length; ti++) { if (preds[ti][0](it, cd, preds[ti][1])) { set[it.k] = 1; break; } } } }
            // the card search for the phrase itself: the strongest matches are excluded as well (names, analogs, mood words the predicates do not know)
            var rs = c.search(ph, { limit: 260 }); if (rs.length) { var top = rs[0].s, nTok = Math.max(1, toks.length); rs.forEach(function (r) { if (r.s >= 0.5 * top && r.hits && r.hits.length >= Math.min(nTok, 2)) set[r.key] = 1; }); }
            AV_CACHE[ph] = set; for (var k1 in set) out[k1] = 1;
        });
        return out;
    }

    function merge2(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }
    var NAMEIDX = null;
    function search(query, o) {
        o = o || {}; var c = CD(), a = AT(); if (!c || !c.ready()) return [];
        if (o.avoid && o.avoid.length) { var avx = avoidSet(o.avoid), ex1 = (o.exclude || []).slice(); for (var ax in avx) ex1.push(ax); o = merge2(o, { exclude: ex1 }); }
        var types = o.types || ['base', 'monolithic'];
        var A = c.search(query, { types: types, own: o.own, limit: 90, exclude: o.exclude, minQ: o.minQ });                // meaning: the finish cards (synonyms, analogs, mood)
        // fused with the old keyword + facet search (matte / satin / chrome / colour words as FACETS) by reciprocal rank: robust for sentences that NAME a finish and for ones that DESCRIBE a look
        // (negated phrases never reach the keyword search: "no chrome, other than satin" must not look for chrome)
        var posQ = String(query || '').replace(/\b(?:anything but|everything but|all but|anything except|everything except|anything besides|anything other than|no|not|without|except|never|minus|avoid|other than|besides|instead of|rather than|don'?t want|do not want|dont want)\s+(?:any\s+|too\s+much\s+|a\s+|the\s+)?[a-z]+(?:\s[a-z]+)?/gi, ' ').replace(/\s+/g, ' ').trim();
        var B = []; try { var tt = types.length === 1 ? types[0] : (types.indexOf('spec') !== -1 || types.indexOf('pattern') !== -1 ? 'any' : 'finish'); if (posQ) B = a.find({ query: posQ, type: tt, own: o.own, limit: 30, diverse: true, min_quality: o.minQ || 40, exclude: o.exclude }) || []; } catch (eb) {}
        var fused = {}, ordr = [], wB = CFG.wB, pinned = {};
        // a finish the painter NAMES wins: its exact name inside the (positive) ask pins it to the top whatever the family / meaning scores say
        try {
            var nq = ' ' + posQ.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' ', ex0 = {}; (o.exclude || []).forEach(function (k) { ex0[k] = 1; });
            if (nq.length > 6) {
                if (!NAMEIDX) { NAMEIDX = []; var dd = a._data().items; for (var ni = 0; ni < dd.length; ni++) { var nn = String(dd[ni].n || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); if (nn.length >= 4) NAMEIDX.push([dd[ni].k, ' ' + nn + ' ', nn.length, dd[ni]._type, dd[ni].o, dd[ni].q]); } }
                NAMEIDX.forEach(function (e) { if (types.indexOf(e[3]) !== -1 && !ex0[e[0]] && !(o.minQ && !(e[5] != null && e[5] >= o.minQ)) && !(o.own === 'own' && e[4] !== 1 && (e[3] === 'base' || e[3] === 'monolithic')) && !(o.own === 'takes' && e[4] === 1 && (e[3] === 'base' || e[3] === 'monolithic')) && nq.indexOf(e[1]) !== -1) pinned[e[0]] = nq === e[1] ? 1000 : 400 + Math.min(e[2], 20) * 5; });
            }
        } catch (ep) {}
        if (A.length && A[0].hits && A[0].hits.length >= 4) wB = CFG.wB * 0.35;                // a rich, descriptive match in the cards (4+ distinct words): trust the meaning search over name / facet matching
        A.forEach(function (r, i) { fused[r.key] = { key: r.key, s: 1.0 / (60 + i), hits: r.hits }; ordr.push(r.key); });
        B.forEach(function (r, i) { if (!fused[r.key]) { fused[r.key] = { key: r.key, s: 0, hits: [] }; ordr.push(r.key); } fused[r.key].s += wB / (60 + i); });
        Object.keys(pinned).forEach(function (k) { if (!fused[k]) { fused[k] = { key: k, s: 0, hits: [] }; ordr.push(k); } });
        var raw = ordr.map(function (k) { return { key: k, s: fused[k].s * 3000 + (pinned[k] || 0), hits: fused[k].hits, pin: !!pinned[k] }; }).filter(function (r) { var hi = a.lookup(r.key); return !(hi && HID_RE.test(hi.n || '')); }).sort(function (x, y) { return y.s - x.s; });
        var out = [], famC = {}, pool = raw.slice(), off = o.offset || 0, limit = off + (o.limit || 8), guard = 0;
        while (out.length < limit && pool.length && guard++ < 500) {
            var bi = 0, bs = -1e9, i;
            for (i = 0; i < Math.min(pool.length, 24); i++) { var it = a.lookup(pool[i].key), f = it ? family(it) : pool[i].key, sc = pool[i].pin ? pool[i].s : pool[i].s * Math.pow(0.6, famC[f] || 0); if (sc > bs) { bs = sc; bi = i; } }
            var p = pool.splice(bi, 1)[0], it2 = a.lookup(p.key); out.push({ key: p.key, name: it2 ? it2.n : p.key, s: p.s, why: p.hits }); var ff = it2 ? family(it2) : p.key; famC[ff] = (famC[ff] || 0) + 1;
        }
        return out.slice(off, limit);
    }

    // ------------------------------------------------------------------ LIKE: finishes similar to one (or a few) finishes, bent by a modifier
    //   SpbProRank.like(refKeys[], {mods:['calm','darker',...], colour:'#hex', lane, exclude[], limit, offset}) -> [{key,name,s,why[],look,loud,busy,mood,pair,avoid,analog}]
    //   similarity = the card search run with the reference's OWN words (search words + analogs + look + mood, never its name), so siblings do not win by name alone
    var SHINE_ORD = { 'matte': 0, 'semi-matte': 1, 'satin': 2, 'gloss': 3, 'high gloss': 4, 'mirror': 5 }, METAL_ORD = { 'none': 0, 'low': 1, 'medium': 2, 'high': 3, 'full': 4 };
    var DARKW = /\b(dark|black|midnight|shadow|noir|obsidian|coal|ink|night|stealth|deep)\b/, LIGHTW = /\b(light|pale|white|pearl|ivory|bright|cream|pastel|snow|ice|silver)\b/, SPARKW = /\b(sparkle|sparkly|glitter|flake|glint|shimmer|diamond|crystal|sequin|stardust)\b/;
    function words(cd, it) { return (it.n + ' ' + cd.look + ' ' + cd.syn.join(' ')).toLowerCase(); }
    var METRIC = {
        dark: function (it, cd) { if (it.o === 1 && it.L != null) return (50 - it.L) / 50; var w = words(cd, it); return DARKW.test(w) ? 0.8 : (LIGHTW.test(w) ? -0.8 : 0); },
        gloss: function (it) { var v = SHINE_ORD[it.shine]; return v == null ? 0 : (v - 2.5) / 2.5; },
        metal: function (it) { var v = METAL_ORD[it.metal]; return v == null ? 0 : (v - 2) / 2; },
        spark: function (it, cd) { var n = 0, m, re = new RegExp(SPARKW.source, 'g'), w = words(cd, it); while ((m = re.exec(w)) && n < 3) n++; return (it.sp != null ? it.sp / 50 : (it.sk === 1 ? 1 : 0)) + 0.3 * n / 3; },      // sp = measured sparkle 0-100 (gunmetal 20, satin 0, a glitter look 100)
        warm: function (it) { if (it.o !== 1 || !it.c || !it.c.length) return 0; var h = hls(it.c[0]); if (!h || h.s < 0.2) return 0; return (h.h < 70 || h.h > 330) ? 1 : (h.h >= 160 && h.h <= 270 ? -1 : 0); },
        vivid: function (it) { return it.o === 1 && it.S != null ? (it.S - 40) / 60 : 0; },
        scale: function (it, cd) { var v = cd.scale ? { fine: 1, medium: 2, broad: 3 }[cd.scale] : { micro: 0, fine: 1, medium: 2, broad: 3, flat: 1.5 }[it.fb]; return v == null ? 0 : (v - 1.5) / 1.5; },
        loud: function (it, cd) { return (cd.loud - 3) / 2; },
        busy: function (it, cd) { return (cd.busy - 3) / 2; }
    };
    // modifier -> [metric, direction, weight]
    var MODMAP = { calm: [['loud', -1, 1.1], ['busy', -1, 0.5]], bold: [['loud', 1, 1.1], ['busy', 1, 0.3]], darker: [['dark', 1, 2.2]], lighter: [['dark', -1, 2.2]], glossier: [['gloss', 1, 2.0]], flatter: [['gloss', -1, 2.0]],
        sparklier: [['spark', 1, 2.0]], smoother: [['spark', -1, 1.8], ['busy', -1, 0.6]], metalmore: [['metal', 1, 1.8]], metalless: [['metal', -1, 1.8]], warmer: [['warm', 1, 1.8]], cooler: [['warm', -1, 1.8]],
        vivid: [['vivid', 1, 1.6]], muted: [['vivid', -1, 1.6]], simpler: [['busy', -1, 1.4]], busier: [['busy', 1, 1.4]], finer: [['scale', -1, 2.2]], coarser: [['scale', 1, 2.2]] };
    var MODWHY = { calm: 'calmer', bold: 'bolder', darker: 'darker', lighter: 'lighter', glossier: 'glossier', flatter: 'flatter', sparklier: 'more sparkle', smoother: 'less sparkle', metalmore: 'more metallic', metalless: 'less metallic', warmer: 'warmer colours', cooler: 'cooler colours', vivid: 'more vivid', muted: 'more muted', simpler: 'simpler', busier: 'more detail', finer: 'finer', coarser: 'coarser' };
    var GENERIC_HIT = { pattern: 1, design: 1, finish: 1, paint: 1, look: 1, color: 1, colour: 1, texture: 1, surface: 1, style: 1, effect: 1, base: 1, layer: 1, modern: 1, special: 1 };
    function palSim(a, b) {         // 0..1 how close the first palette colours of two complete looks are
        var pa = hls((a.c || [])[0]), pb = hls((b.c || [])[0]); if (!pa || !pb) return 0.4;
        var dl = Math.abs(pa.l - pb.l); if (pa.s < 0.14 || pb.s < 0.14) return (pa.s < 0.14 && pb.s < 0.14) ? Math.max(0, 1 - dl * 2) : Math.max(0, 0.35 - dl);
        return Math.max(0, 1 - hueDist(pa.h, pb.h) / 70) * Math.max(0, 1 - dl * 1.6);
    }
    function like(refs, o) {
        o = o || {}; var c = CD(), a = AT(); if (!c || !c.ready() || !a) return [];
        refs = (refs || []).filter(function (k) { return a.lookup(k) && c.card(k); }); if (!refs.length) return [];
        var r0 = a.lookup(refs[0]), t0 = r0._type, tex = t0 === 'spec' || t0 === 'pattern', types = tex ? [t0] : ['base', 'monolithic'];
        var cds = refs.map(function (k) { return c.card(k); }), q = [];
        cds.forEach(function (cd) { q.push(cd.syn.join(' ')); q.push(cd.analog.join(' ')); q.push(cd.look); q.push(cd.mood.join(' ')); });
        var avl = []; if (o.avoid && o.avoid.length) { var avy = avoidSet(o.avoid); for (var ay in avy) avl.push(ay); }
        var A = c.search(q.join(' '), { types: types, limit: 260, exclude: (o.exclude || []).concat(refs, avl) });
        if (!A.length) return [];
        var maxS = A[0].s || 1, cd0 = cds[0], mods = (o.mods || []).filter(function (m) { return MODMAP[m]; }), col = o.colour ? hls(o.colour) : null, rows = [];
        var refLoud = 0, refBusy = 0; cds.forEach(function (cd) { refLoud += cd.loud; refBusy += cd.busy; }); refLoud /= cds.length; refBusy /= cds.length;
        A.forEach(function (r) {
            var it = a.lookup(r.key), cd = c.card(r.key); if (!it || !cd || HID_RE.test(it.n || '')) return;
            if (o.lane === 'keep' && !(it.o === 0 && !tex)) return; if (o.lane === 'complete' && !(it.o === 1 && !tex)) return;
            var s = CFG.likeSim * (r.s / maxS), why = [], hit = (r.hits || []).filter(function (w) { return !GENERIC_HIT[w] && w.length > 2; }).slice(0, 3);
            if (hit.length) why.push('shares ' + hit.join(', '));
            if (!mods.length) { s -= 0.3 * Math.abs(cd.loud - refLoud) + 0.2 * Math.abs(cd.busy - refBusy); }
            if (!tex && !o.mixLane && it.o !== r0.o) s -= (r0.o === 0 ? 1.1 : 0.5);
            if (!tex && r0.o === 1 && it.o === 1 && !mods.some(function (m) { return m === 'warmer' || m === 'cooler' || m === 'vivid' || m === 'muted' || m === 'darker' || m === 'lighter'; })) { var ps = palSim(it, r0); s += CFG.likePal * ps; if (ps >= 0.8) why.push('a similar palette'); }      // two complete looks: a similar palette (hue / lightness) is part of "like this\"      // a shine-only finish stays shine-only (it keeps the part's colour); a complete look stays a complete look
            mods.forEach(function (m) {
                MODMAP[m].forEach(function (spec) {
                    var f = METRIC[spec[0]], delta = 0;
                    delta = f(it, cd) - cds.reduce(function (acc, cdr, i) { return acc + f(a.lookup(refs[i]), cdr); }, 0) / cds.length;
                    var g = spec[1] * delta * spec[2] * CFG.likeMod; s += Math.max(-spec[2] * 1.2 * CFG.likeMod, Math.min(spec[2] * 1.6 * CFG.likeMod, g));
                    if (spec[1] * delta > 0.35 && why.indexOf(MODWHY[m]) === -1) why.push(MODWHY[m]);
                    if (spec[1] * delta <= 0.05) s -= (spec[1] * delta < -0.2 ? 0.9 : 0.5) * spec[2] * CFG.likeMod;        // no movement / the wrong way: out
                });
            });
            if (col && it.o === 1 && it.c && it.c.length) { var ph = hls(it.c[0]); if (ph && ph.s > 0.2 && col.s > 0.2) { var dd = hueDist(ph.h, col.h); if (dd <= 28) { s += 2.0; why.push('in that colour'); } else if (dd > 90) s -= 1.2; } else if (ph && ph.s <= 0.2 && col.s > 0.2) s -= 0.6; }
            s += 0.45 * (cd.appeal - 3) - 0.3 * (cd.risk - 2.5);
            if (it.q != null) s += (it.q - 60) / 80;
            rows.push({ key: r.key, name: it.n, s: s, why: why, it: it, cd: cd });
        });
        rows.sort(function (x, y) { return y.s - x.s; });
        var out = [], famC = {}, off = o.offset || 0, lim = off + (o.limit || 5), pool = rows.slice(0, 80), guard = 0;
        while (out.length < lim && pool.length && guard++ < 500) {
            var bi = 0, bs = -1e9, i;
            for (i = 0; i < Math.min(pool.length, 20); i++) { var f = family(pool[i].it), sc = pool[i].s * Math.pow(0.5, famC[f] || 0); if (pool[i].s < 0) sc = pool[i].s - 0.8 * (famC[f] || 0); if (sc > bs) { bs = sc; bi = i; } }
            var p = pool.splice(bi, 1)[0]; out.push(p); var ff = family(p.it); famC[ff] = (famC[ff] || 0) + 1;
        }
        return out.slice(off, lim).map(function (r) { return { key: r.key, name: r.name, s: r.s, why: r.why, look: r.cd.look, loud: r.cd.loud, busy: r.cd.busy, mood: r.cd.mood, use: r.cd.use, pair: r.cd.pair, avoid: r.cd.avoid, analog: r.cd.analog, lane: tex ? 'texture' : (r.it.o === 1 ? 'complete' : 'keep') }; });
    }
    window.SpbProRank = { suggest: suggest, search: search, like: like, avoidSet: avoidSet, isTrait: isTrait, harmony: harmony, GOALS: GOALS, MODS: MODMAP, _cfg: CFG };
})();
