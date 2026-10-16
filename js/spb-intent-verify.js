/* ============================================================================
   HELPER V3 S2 2026-10-05 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md section 2.4, stage A): the STATIC VERIFIER.
   Before any change is committed, its scope is checked against what the SENTENCE allows (js/spb-intent-frame.js read():
   the parts / layers / elements it names, its keep-clauses, the conversation's focus) plus the protected decal / number /
   sponsor layers. Two places, every path:
     onRoute(text, env, r)   offline helper + guided builder: the routed plan (builder steps), before the builder shows it.
                             Symbolic (no pixels), so the Node graders see exactly what the app does.
     onQueue(queue, o)       js/spb-pro-ai.js applyQueue (offline Run, DeepSeek tool loop, MCP): the zone regions, measured
                             with the zone kit (probeRegion), before anything is applied.
   Verdicts: ok | repair (the plan is cut down to the allowed scope, said in a note) | ask (rolled back: nothing changes,
   one honest question). Mode (window var or localStorage key SPB_AI_VERIFY): 'enforce' (default) | 'warn' (log only:
   the finding rides in the turn log "verify" field, the plan is untouched) | 'off'. SPB_AI_FRAME = '0' = off too.
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    function IF() { return W.SpbIntentFrame; }
    function mode() { var F = IF(); if (!F || !F.on()) return 'off'; var m = String(F.flag('SPB_AI_VERIFY', 'enforce')).toLowerCase(); return /^(off|warn|enforce)$/.test(m) ? m : 'enforce'; }
    function clone(o) { return o == null ? o : JSON.parse(JSON.stringify(o)); }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function B() { return W.SpbOfflineBuilder; }
    var LOG = [];
    function logV(v) { try { v.t = Date.now(); LOG.push(v); if (LOG.length > 40) LOG.shift(); } catch (e) {} return v; }

    // ------------------------------------------------------------------ colour family (same rule as the bank grader / normalise.py)
    function hexFamily(h) {
        h = String(h || '').replace('#', ''); if (!/^[0-9a-f]{6}$/i.test(h)) return null;
        var r = parseInt(h.slice(0, 2), 16) / 255, g = parseInt(h.slice(2, 4), 16) / 255, b = parseInt(h.slice(4, 6), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), v = mx, s = mx ? (mx - mn) / mx : 0, hh = 0;
        if (mx !== mn) { var d = mx - mn; hh = mx === r ? ((g - b) / d + (g < b ? 6 : 0)) : mx === g ? ((b - r) / d + 2) : ((r - g) / d + 4); hh *= 60; }
        if (v < 0.2) return 'black'; if (s < 0.15) return v > 0.86 ? 'white' : (v > 0.6 ? 'silver' : 'grey');
        if (hh < 14 || hh >= 345) return 'red'; if (hh < 40) return v < 0.5 ? 'brown' : 'orange'; if (hh < 50) return 'gold'; if (hh < 66) return 'yellow';
        if (hh < 165) return 'green'; if (hh < 195) return 'teal'; if (hh < 255) return 'blue'; if (hh < 290) return 'purple'; return 'pink';
    }
    function colourMatches(c, words) {
        if (!c) return false; var nm = String(c.name || '').toLowerCase(), fam = hexFamily(c.hex);
        return words.some(function (w) { return nm.indexOf(w) !== -1 || fam === w || (w === 'grey' && fam === 'silver') || (w === 'silver' && fam === 'grey'); });
    }

    // ------------------------------------------------------------------ layers: which ones are decals / numbers (never touched unless named)
    function layerRole(name, env) {
        var L = ((env && env.layers) || []).filter(function (l) { return l && l.name === name; })[0], role = String((L && L.role) || '').toLowerCase(), n = String(name || '').toLowerCase();
        if (/number/.test(role) || /^numbers?$/.test(n)) return 'numbers';
        if (/decal|logo|sponsor/.test(role) || /logo|decal|sponsor|contingenc/.test(n)) return 'sponsors';
        if (/body/.test(role) || /\bbase\b/.test(n)) return 'body';
        return 'other';
    }
    // what a builder step touches: { k: body|part|colourWide|colourParts|layer|element|box|other, parts, layers, element }
    function touchOf(st, env) {
        var w = st && st.what; if (!w) return { k: 'other' };
        if (w.k === 'body' || w.k === 'main') return { k: 'body' };
        if (w.k === 'part') return { k: 'part', parts: [String(w.part || '').split('@')[0]] };
        if (w.k === 'numbers') return { k: 'element', element: 'numbers' };
        if (w.k === 'sponsors') return { k: 'element', element: 'sponsors' };
        if (w.k === 'box') return { k: 'box' };
        if (w.k === 'layer') { var ls = (w.layers || (w.tg && w.tg.layers) || []).slice(), roles = ls.map(function (l) { return layerRole(l, env); }); var dec = roles.filter(function (r) { return r === 'numbers' || r === 'sponsors'; }); return dec.length ? { k: 'element', element: dec[0], layers: ls, viaLayer: true } : { k: roles.every(function (r) { return r === 'body'; }) ? 'body' : 'layer', layers: ls }; }
        if (w.k === 'colour') {
            var tg = w.tg || {}, lay = tg.layers || [], pr = (tg.parts || []).map(function (p) { return String(p).split('@')[0]; });
            if (lay.length) { var rl = lay.map(function (l) { return layerRole(l, env); }), dc = rl.filter(function (r) { return r === 'numbers' || r === 'sponsors'; }); if (dc.length) return { k: 'element', element: dc[0], layers: lay, viaLayer: true, colour: true }; }
            return pr.length ? { k: 'colourParts', parts: pr } : (lay.length ? { k: 'layer', layers: lay } : { k: 'colourWide' });
        }
        return { k: 'other' };
    }
    function stepNamesElement(rd, el, layers) {
        if (rd.decals === 'include') return true;
        if (rd.elements.indexOf(el) !== -1) return true;
        return (layers || []).some(function (l) { return rd.layers.indexOf(l) !== -1; });
    }

    // ------------------------------------------------------------------ the conversation's focus (what "it / them / make it white" is about)
    var FOCUS = null, PEND = null, PREVF = null;          // HELPER V3 S3: PREVF = the focus before the current sentence
    function focusFromLast(last) {
        if (!last || !last.targets || !last.targets.length) return null;
        var f = { parts: [], layers: [], elements: [], unresolved: [], whole: false, from: 'last change' };
        last.targets.forEach(function (t) {
            if (!t) return;
            if (t.kind === 'part') f.parts.push(String(t.part || '').split('@')[0]);
            else if (t.kind === 'colour' && t.parts && t.parts.length) t.parts.forEach(function (p) { f.parts.push(String(p).split('@')[0]); });
            else if (t.kind === 'numbers' || t.kind === 'sponsors') f.elements.push(t.kind);
            else if ((t.kind === 'layer' || t.kind === 'layerword') && (t.layers || t.word)) [].concat(t.layers || [t.word]).forEach(function (l) { f.layers.push(l); });
            else f.whole = true;
        });
        f.parts = uniq(f.parts); return f;
    }
    function focusNow(env) {
        if (FOCUS) return FOCUS;
        if (env && env.last && env.inConvo !== false) return focusFromLast(env.last);
        return null;
    }
    function narrow(f) { return !!(f && !f.whole && (f.parts.length || f.layers.length || f.elements.length || f.unresolved.length)); }
    function remember(rd, steps, env) {
        var f = { parts: [], layers: [], elements: [], unresolved: [], whole: false, from: 'this chat' }, any = false;
        (steps || []).forEach(function (st) {
            var t = touchOf(st, env); if (st.what && st.what.k === 'step') return;
            if (t.k === 'part' || t.k === 'colourParts') { t.parts.forEach(function (p) { f.parts.push(p); }); any = true; }
            else if (t.k === 'element') { if (t.viaLayer) (t.layers || []).forEach(function (l) { f.layers.push(l); }); else f.elements.push(t.element); any = true; }
            else if (t.k === 'layer') { (t.layers || []).forEach(function (l) { f.layers.push(l); }); any = true; }
            else if (t.k === 'body' || t.k === 'colourWide') { f.whole = true; any = true; }
        });
        if (!any) {
            if (rd.whole) { f.whole = true; any = true; }
            else if (rd.parts.length || rd.layers.length || rd.unresolved.length || rd.fuzzy.length || rd.elements.filter(function (e) { return e !== 'stripes'; }).length) {
                f.parts = rd.parts.slice(); f.layers = rd.layers.slice(); f.elements = rd.elements.filter(function (e) { return e !== 'stripes'; }); f.unresolved = rd.unresolved.concat(rd.fuzzy.map(function (z) { return z.said; })); any = true;
            }
        }
        if (any) { f.parts = uniq(f.parts); f.layers = uniq(f.layers); f.elements = uniq(f.elements); FOCUS = f; }
    }

    // ------------------------------------------------------------------ step surgery (builder steps; new ids from the builder)
    function chainOf(steps, id) { var out = []; steps.forEach(function (s) { if (s.what && s.what.k === 'step' && s.what.ref === id) { out.push(s); out = out.concat(chainOf(steps, s.id)); } }); return out; }
    function mk(o) { var b = B(); var c = clone(o); delete c.id; return b && b.newStep ? b.newStep(c) : Object.assign({ id: 's' + Math.random().toString(36).slice(2, 8) }, c); }
    function retarget(steps, st, whats) {          // st + its chained steps -> one copy per new "what"
        var ch = chainOf(steps, st.id), out = [];
        whats.forEach(function (wh) { var r0 = mk(st); r0.what = wh; out.push(r0); var idMap = {}; idMap[st.id] = r0.id; ch.forEach(function (c) { var c2 = mk(c); c2.what = { k: 'step', ref: idMap[c.what.ref] || r0.id }; idMap[c.id] = c2.id; out.push(c2); }); });
        var drop = [st].concat(ch), at = steps.indexOf(st), keep = steps.filter(function (s) { return drop.indexOf(s) === -1; });
        var before = keep.filter(function (s) { return steps.indexOf(s) < at; }), after = keep.filter(function (s) { return steps.indexOf(s) > at; });
        return before.concat(out, after);
    }
    function dropStep(steps, st) { var d = [st].concat(chainOf(steps, st.id)); return steps.filter(function (s) { return d.indexOf(s) === -1; }); }
    function lookKey(st) { return JSON.stringify([st.act, st.colour ? (st.colour.hex || st.colour.name) : null, st.finish ? st.finish.key || st.finish.label : null, st.tex ? st.tex.id : null]); }
    function whatFor(f) {          // focus -> new step targets
        if (f.parts.length) return f.parts.map(function (p) { return { k: 'part', part: p }; });
        if (f.layers.length) return f.layers.map(function (l) { return { k: 'layer', layers: [l], word: l }; });
        if (f.elements.length) return f.elements.filter(function (e) { return e === 'numbers' || e === 'sponsors'; }).map(function (e) { return { k: e }; });
        return [];
    }
    function partsLabel(ps) { return ps.length > 1 ? ps.slice(0, -1).join(', ') + ' and ' + ps[ps.length - 1] : ps[0]; }

    // ------------------------------------------------------------------ stage A, symbolic: the routed plan vs the sentence
    function plan(text, env, steps0) {
        var said = null, F = IF(), rd = keepMore(bindTypo(lookless(F.read(text, env), text), text), text, F), steps = clone(steps0), fx = [], notes = [], ask = null, focus = focusNow(env);
        var droppedKeep = null, roots = function () { return steps.filter(function (s) { return s.what && s.what.k !== 'step'; }); };
        var namedEls = rd.elements.filter(function (e) { return e !== 'stripes'; });
        // (1) keep-clauses: a kept part / element is never touched
        roots().forEach(function (st) {
            var t = touchOf(st, env);
            if ((t.k === 'part' || t.k === 'colourParts') && t.parts.some(function (p) { return rd.keep.parts.indexOf(p) !== -1; })) {
                var left = t.parts.filter(function (p) { return rd.keep.parts.indexOf(p) === -1; });
                fx.push({ code: 'kept', what: t.parts.join('+') });
                if (!droppedKeep) droppedKeep = clone(st);
                if (t.k === 'part' || !left.length) steps = dropStep(steps, st); else st.what.tg.parts = left;
            } else if (t.k === 'element' && rd.keep.elements.indexOf(t.element) !== -1) { fx.push({ code: 'kept', what: t.element }); steps = dropStep(steps, st); }
            else if ((t.k === 'body' || t.k === 'colourWide') && rd.keep.parts.length) {
                var ex = (st.extra && st.extra.exclude) || [], miss = rd.keep.parts.filter(function (p) { return ex.indexOf(p) === -1; });
                if (miss.length) { fx.push({ code: 'kept-exclude', what: miss.join('+') }); st.extra = st.extra || {}; st.extra.exclude = ex.concat(miss); }
            }
        });
        if (!roots().length && droppedKeep && (rd.whole || /\b(?:all (?:the )?parts|every ?thing|all over)\b/i.test(String(text)))) {
            var bs = mk(droppedKeep); bs.what = { k: 'body' }; bs.extra = Object.assign({}, bs.extra || {}, { exclude: rd.keep.parts.slice() }); steps = [bs];
            fx.push({ code: 'kept-invert', what: 'whole car minus ' + rd.keep.parts.join('+') });
        }
        var subHard = rd.keep.sub.filter(function (x) { return /around|else|rest/i.test(x); });
        if (subHard.length && roots().some(function (st) { var t = touchOf(st, env); return t.k === 'element' || t.k === 'body' || t.k === 'colourWide'; }) && !rd.whole) {
            fx.push({ code: 'kept-sub', what: subHard.join('+') });
            ask = 'I cannot change that and keep “' + subHard[0] + '” as it is in the same step: the app selects the whole ' + (namedEls[0] === 'numbers' ? 'number' : namedEls[0] === 'sponsors' ? 'logo' : 'area') + ' by colour or layer, so the ' + subHard[0] + ' would change too. Nothing was changed. Draw a box around the exact part to change, or pick its colour under Where.';
        }
        // (2) decals / numbers / sponsors: only when named, and only with the colour the sentence gives them
        if (!ask) roots().forEach(function (st) {
            var t = touchOf(st, env); if (t.k !== 'element') return;
            if (!stepNamesElement(rd, t.element, t.layers)) { fx.push({ code: 'decal', what: t.element }); steps = dropStep(steps, st); return; }
            var bw = rd.bound[t.element]; if (!bw || !(rd.whole || rd.parts.length || roots().some(function (s3) { return s3 !== st && touchOf(s3, env).k !== 'element'; }))) return;          // "all black with white numbers" / "hood black w a white number": the colour DESCRIBES them
            if (st.act === 'recolour' ? !colourMatches(st.colour, bw) : true) { fx.push({ code: 'decal-colour', what: t.element + ' stay ' + bw.join('/') }); steps = dropStep(steps, st); }
        });
        var noAlias = rd.unresolved.concat(rd.fuzzy.map(function (z) { return z.maybe; })).filter(function (w) { return /^(?:the )?(?:mirrors?|windows?|wind ?shield|glass|pillars?|roll ?cage|cage|vents?|scoops?|intakes?|wheels?|rims?)$/i.test(String(w)); });          // words no car-map part stands in for (a splitter IS the front bumper, fenders ARE the sides)
        if (!ask && noAlias.length && !rd.whole) roots().forEach(function (st) {
            if (ask) return; var t = touchOf(st, env); if (t.k !== 'part') return;
            if (rd.parts.indexOf(t.parts[0]) !== -1 || (focus && focus.parts.indexOf(t.parts[0]) !== -1 && !rd.unresolved.concat(rd.fuzzy.map(function (z) { return z.maybe; })).length)) return;
            var un = noAlias[0]; said = rd.unresolved.indexOf(un) !== -1 ? un : ((rd.fuzzy.filter(function (z) { return z.maybe === un; })[0] || {}).said || un);
            fx.push({ code: 'outside', what: 'the ' + t.parts[0] + ' for “' + un + '”' });
            ask = { pendWhich: true, text: 'I cannot find “' + un + '” on the car map (it knows the hood, roof, trunk, spoiler, bumpers and sides), and I would have changed the ' + t.parts[0] + ' instead, so nothing was changed. Draw a box around it, or name one of those parts.', chips: ['Draw a box around it'] };
        });
        // (2b) "add a pinline between the black hood and white roof": colours inside a between-clause DESCRIBE the parts (in-app bank A-0221 repainted the roof)
        var btw = /\bbetween\s+(?:the\s+)?(.{2,40}?)\s+and\s+(?:the\s+)?(.{2,40}?)(?=[,.;!?]|$|\s+(?:on|of|with|in)\b)/i.exec(String(text || ''));
        if (!ask && btw && /\b(?:pin ?lines?|lines?|stripes?|borders?|outlines?|trim|bands?|seams?)\b/i.test(text)) {
            var bp = []; try { bp = (F.partsOf(btw[1]) || []).concat(F.partsOf(btw[2]) || []).map(function (x) { return String(x).split('@')[0]; }); } catch (eb) { bp = []; }
            roots().forEach(function (st) { var t = touchOf(st, env); if (st.act === 'recolour' && t.k === 'part' && bp.indexOf(t.parts[0]) !== -1) { fx.push({ code: 'described', what: t.parts[0] + ' colour is a description' }); steps = dropStep(steps, st); } });
            if (fx.some(function (f) { return f.code === 'described'; }) && !roots().length) ask = { text: 'Nothing was changed: I read “' + btw[1] + '” and “' + btw[2] + '” as how those parts look now, not as changes. A line between two parts is drawn with the stripe tool, or tell me one part to outline (for example “a thin yellow outline on the hood”).', chips: ['A thin yellow outline on the hood'] };
        }
        // (2c) a typo'd side ("the rgiht door") while the plan paints BOTH sides: keep the side the typo means
        var sideT = null; String(text || '').toLowerCase().replace(/[a-z]+/g, function (w) { if (sideT || w === 'right' || w === 'left' || w.length < 4 || w.length > 6) return w; ['right', 'left'].forEach(function (c) { if (!sideT && dl(w, c) === 1 && w.split('').sort().join('') === c.split('').sort().join('')) sideT = c; }); return w; });
        if (!ask && sideT && !/\b(?:both|doors|sides)\b/i.test(text)) {
            var other = sideT === 'right' ? 'left side' : 'right side';
            roots().forEach(function (st) { var t = touchOf(st, env); if (t.k === 'part' && t.parts[0] === other && roots().some(function (s2) { var t2 = touchOf(s2, env); return t2.k === 'part' && t2.parts[0] === sideT + ' side'; })) { fx.push({ code: 'outside', what: other + ' for a typo of ' + sideT }); steps = dropStep(steps, st); } });
        }
        // (3) whole-car steps: only when the sentence (or the conversation) means the whole car
        if (!ask) roots().forEach(function (st) {
            if (ask) return; var t = touchOf(st, env); if (t.k !== 'body' && t.k !== 'colourWide') return;
            if (rd.whole) return;
            if (rd.unresolved.length || rd.fuzzy.length) {
                if (t.k === 'colourWide' && !rd.parts.length) return;          // "the red" is a named colour target
                var fz = rd.fuzzy[0], un = rd.unresolved[0];
                said = fz ? fz.said : un;
                if (fz && !un && /^(?:mirrors?|fenders?|tail ?gate|bonnet|nose|bed)$/i.test(fz.maybe) && !/bonnet/i.test(fz.maybe)) { un = fz.maybe; fz = null; }
                fx.push({ code: 'outside', what: 'whole car for “' + (fz ? fz.said : un) + '”' });
                ask = fz ? 'Did you mean the ' + fz.maybe + '? “' + fz.said + '” is not a part name I know, and I would have changed the whole car, so nothing was changed.' : 'I cannot find “' + un + '” on the car map (it knows the hood, roof, trunk, spoiler, bumpers and sides), and I would have changed the whole car, so nothing was changed. Draw a box around it, or name one of those parts.';
                ask = { text: ask, chips: fz ? [String(text).replace(new RegExp('\\b' + fz.said + '\\b', 'i'), fz.maybe)] : ['Draw a box around it', 'The whole car'], pendWhich: true };
                return;
            }
            if (rd.parts.length) {
                if (t.k === 'colourWide') { fx.push({ code: 'outside', what: (st.what.tg && st.what.tg.word || 'colour') + ' everywhere -> ' + rd.parts.join('+') }); st.what.tg = clone(st.what.tg); st.what.tg.parts = rd.parts.slice(); return; }
                var ps = roots().filter(function (s2) { var t2 = touchOf(s2, env); return s2 !== st && (t2.k === 'part' || t2.k === 'colourParts') && t2.parts.some(function (p) { return rd.parts.indexOf(p) !== -1; }); });
                if (ps.some(function (s2) { return lookKey(s2) === lookKey(st); })) { fx.push({ code: 'outside', what: 'duplicate whole-car ' + st.act }); steps = dropStep(steps, st); return; }
                if (ps.some(function (s2) { return s2.act === st.act; })) return;          // "white body, black roof, red hood": the body is the rest of the car (later part steps win), already right
                fx.push({ code: 'outside', what: 'whole car -> ' + rd.parts.join('+') });
                steps = retarget(steps, st, rd.parts.map(function (p) { return { k: 'part', part: p }; }));
                notes.push('Kept to the ' + partsLabel(rd.parts) + ' (the part' + (rd.parts.length > 1 ? 's' : '') + ' you named), not the whole car.');
                return;
            }
            if (rd.layers.length) { fx.push({ code: 'outside', what: 'whole car -> layer ' + rd.layers.join('+') }); steps = retarget(steps, st, rd.layers.map(function (l) { return { k: 'layer', layers: [l], word: l }; })); return; }
            if (namedEls.length) {
                if (t.k === 'colourWide') return;
                var elSteps = roots().filter(function (s2) { return touchOf(s2, env).k === 'element'; });
                fx.push({ code: 'outside', what: 'whole car beside the ' + namedEls.join('+') });
                if (elSteps.length) steps = dropStep(steps, st);
                else ask = { text: 'You named the ' + namedEls[0] + ', and I would have changed the whole car, so nothing was changed. Tap them under Where, or say “the whole car” if you meant everything.', chips: ['The whole car'] };
                return;
            }
            if (t.k === 'colourWide') return;
            if (rd.elements.indexOf('stripes') !== -1 && !/\b(?:body|base|livery|with (?:an? |some |\w+ )?(?:\w+ )?stripes?|and (?:an? )?(?:\w+ )?stripes?)\b/i.test(text)) {
                var cm = String(text).match(/stripes?\s+(?:is|are|=)\s+(?:a\s+)?([a-z]+)/i), was = cm ? cm[1].replace(/(.)\1+/g, '$1') : '', to = st.colour && st.colour.name ? String(st.colour.name).toLowerCase() : '';
                fx.push({ code: 'outside', what: 'whole car for the stripes' });
                ask = { text: 'I would have changed the whole car, so nothing was changed: stripes are not a part I can select by name.' + (was && to ? ' If they are the only ' + was + ' on the car, the colour swap below changes just them.' : ' Tap the stripe colour under Where, or draw a box around them.'), chips: was && to ? ['Swap the ' + was + ' to ' + to] : ['Draw a box around it'] };
                return;
            }
            if (narrow(focus) && env && env.inConvo !== false) {          // a follow-up never widens the scope (architecture rule 3)
                if (focus.unresolved.length && !focus.parts.length && !focus.layers.length) { fx.push({ code: 'outside', what: 'whole car after “' + focus.unresolved[0] + '”' }); ask = { pendWhich: true, text: 'Which part do you mean? Earlier you named “' + focus.unresolved[0] + '”, which is not on the car map, and this would change the whole car, so nothing was changed. Name a part (hood, roof, trunk, spoiler, bumpers, sides) or draw a box.', chips: ['The whole car'] }; return; }
                var wh = whatFor(focus); if (!wh.length) return;
                fx.push({ code: 'outside', what: 'follow-up widened to the whole car -> ' + (focus.parts.join('+') || focus.layers.join('+') || focus.elements.join('+')) });
                steps = retarget(steps, st, wh);
                notes.push('Kept to the ' + partsLabel(focus.parts.length ? focus.parts : (focus.layers.length ? focus.layers.map(function (l) { return l + ' layer'; }) : focus.elements)) + ' we were working on. Say “the whole car” to change everything.');
            }
        });
        return { rd: rd, fx: fx, steps: steps, notes: notes, ask: ask, said: said };
    }
    function lookless(rd, text) {          // "hood n roof like a mirror": a look word, not a region the car map lacks
        var t = String(text || '').toLowerCase(), isLook = function (w) { w = String(w || '').toLowerCase().replace(/^the\s+/, ''); return new RegExp('(?:like|as) (?:a |an )?' + w + '|' + w + '[- ]?(?:finish|shine|look|effect)').test(t) || (/^mirror$/.test(w) && /\bmirror(?:ed)? (?:that|it|this|them|those|these|the (?:look|design|same|whole)|on|onto|to|across)\b/.test(t)); };
        rd.unresolved = rd.unresolved.filter(function (w) { return !isLook(w); }); rd.fuzzy = rd.fuzzy.filter(function (z) { return !isLook(z.said); }); return rd;
    }
    var COLW = ['white', 'black', 'red', 'blue', 'green', 'yellow', 'orange', 'gold', 'silver', 'grey', 'gray', 'pink', 'purple'];
    function bindTypo(rd, text) {          // "all black with whhite numbers": the numbers' own colour, typo or not
        ['numbers', 'sponsors'].forEach(function (el) {
            if (rd.bound[el]) return;
            var m = String(text || '').toLowerCase().match(el === 'numbers' ? /\b([a-z]+)\s+(?:numbers?|#s?)\b/ : /\b([a-z]+)\s+(?:sponsors?|logos?|decals?)\b/); if (!m) return;
            var w = m[1].replace(/(.)\1+/g, '$1'), hit = COLW.filter(function (c) { return c.replace(/(.)\1+/g, '$1') === w; })[0];
            if (hit) rd.bound[el] = [hit === 'gray' ? 'grey' : hit];
        });
        return rd;
    }
    // a bare look as the first words of a chat ("red", "matte black"): which part is the buyer's call, not the whole car by default
    var BARE_RE = /^\s*(?:red|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple|white|black|teal|chrome|carbon|matte|satin)\s*[.!]*\s*$/i;
    function keepMore(rd, text, F) {          // "everything white but the hood" / "all blue without the spoiler" / "except the sponsor panels and the hood": the kept list, whole
        var re = /\b(?:but|without|except(?: for)?|apart from|other than|leave|leaving)\s+((?:the |my |both )?[a-z ]{3,60}?)(?=\s*(?:[,.;!]|$|\b(?:which|that|stays?|alone|as is|untouched|w\/|with)\b))/gi, m, t = String(text || '');
        while ((m = re.exec(t))) {
            if (new RegExp('\\b(?:' + COLW.join('|') + ')\\b', 'i').test(m[1])) continue;          // "hood red but the roof blue": a second change, not a keep
            var ps = []; try { ps = F.partsOf(m[1]) || []; } catch (e) { ps = []; }
            ps.forEach(function (p) { p = String(p).split('@')[0]; if (rd.keep.parts.indexOf(p) === -1) rd.keep.parts.push(p); var i = rd.parts.indexOf(p); if (i !== -1) rd.parts.splice(i, 1); });
        }
        return rd;
    }
    function dl(a, b) {          // Damerau-Levenshtein (optimal string alignment)
        var m = a.length, n = b.length, d = [], i, j; for (i = 0; i <= m; i++) { d[i] = [i]; } for (j = 0; j <= n; j++) d[0][j] = j;
        for (i = 1; i <= m; i++) for (j = 1; j <= n; j++) { var c = a[i - 1] === b[j - 1] ? 0 : 1; d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c); if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1); }
        return d[m][n];
    }
    // "In the Logos layr swap the red to #E4002B" / "in the Car_Decal layer make the white parts chrome": ONE colour inside ONE layer, never the whole layer
    // (in-app bank A-0079 turned every logo red; A-0049 chromed the whole decal layer). Re-read as "make the red in the Logos layer #E4002B", which the helper reads right.
    var SWAPPING = false;
    function swapInLayer(text, env, st0) {
        var t = String(text || ''), cw = COLW.concat(['grey']).join('|');
        var m1 = new RegExp('\\b(?:swap|change|turn|make|recolou?r)\\s+(?:all\\s+)?(?:of\\s+)?(?:the\\s+)?(' + cw + ')(?:\\s+(?:parts?|bits?|areas?|pixels?|ones?|bits))?\\s+(?:(?:to|into|for|with)\\s+)?(.{2,40}?)\\s*[.!]*$', 'i').exec(t);
        if (!m1) return null;
        var L = null; ((env && env.layers) || []).forEach(function (l) { var n = String(l && l.name || ''); if (!L && n.length > 2 && new RegExp('\\b' + n.replace(/[^a-z0-9]/gi, '.') + '\\b', 'i').test(t)) L = n; });
        if (!L) return null;
        var whole = (st0 || []).filter(function (st) { var tt = touchOf(st, env); return st.what && st.what.k !== 'step' && (tt.k === 'layer' || (tt.k === 'element' && !tt.colour)); });
        if (!whole.length) return null;
        var c2 = m1[2].replace(/^(?:the\s+)?(?:in|on)\s+the\s+\S+\s+lay\w*\s*/i, '').trim(); if (!c2 || new RegExp('^(?:' + cw + ')$', 'i').test(m1[1]) === false) return null;
        var say2 = 'make the ' + m1[1].toLowerCase() + ' in the ' + L + ' layer ' + c2, OA = W.SpbOfflineAnswer, r2 = null;
        SWAPPING = true; try { r2 = OA && OA.route ? OA.route(say2, env) : null; } catch (e) { r2 = null; } SWAPPING = false;
        if (!r2 || r2.cls !== 'DO' || !(r2.steps || []).some(function (st) { return st.what && st.what.k === 'colour' && st.what.tg && (st.what.tg.layers || []).indexOf(L) !== -1; })) return null;
        r2.v3 = logV({ stage: 'A', mode: 'enforce', verdict: 'repair', findings: [{ code: 'outside', what: 'whole ' + L + ' layer -> only its ' + m1[1].toLowerCase() }], producer: 'offline' });
        return r2;
    }
    function askResult(r, a, why) {
        var q = typeof a === 'string' ? { text: a, chips: [] } : a;
        return { cls: 'ASK', why: 'v3-' + why, ask: { text: q.text, chips: (q.chips || []).slice(0, 4) }, steps: [], via: 'v3-verify', v3: null, _orig: r ? { cls: r.cls, via: r.via, steps: (r.steps || []).length } : null };
    }
    // strong question / options forms that reached a change (rule 5: a question never produces ops)
    function questionAsk(text, rd, steps) {
        var t = String(text || '');
        var ADV = /\b(?:give me (?:some )?id[ea]+s+|id[ea]+s+ for|pick (?:some |the )?colou?rs? for (?:me|us)|suggest|recommend|surprise me|(?:a car|one) like .{2,40} but different)\b/i;
        var IMP = /^\s*(?:(?:ok|okay|so|and|then|now|pls|please|yes|yeah|no)[\s,]+)*(?:make|paint|turn|change|do|go|give|put|add|swap|set|use|try|apply|switch|lighten|darken|bump|drop|keep|leave|take|remove|undo|redo|show|let'?s)\b/i;
        if (!IMP.test(t) && /\b(?:looks?|made|makes|seems?|they'?re|it'?s|is|are)\b.{0,40}\b(?:boring|worse|bad|ugly|weird|wrong|fine|readable|perfect|dull)\b/i.test(t)) return { text: 'Got it. Nothing was changed. Tell me what to change, for example “make the hood brighter”, or tap Undo on the last change.', chips: [] };
        if (rd.options || ADV.test(t)) return { text: 'That sounds like you want to see options first, so nothing was changed. Tap “Do it” to apply this now, or ask “show me <look> finishes” to compare.', chips: ['Do it: ' + t.replace(/\?+\s*$/, '')] };
        if (rd.q && (rd.qmark || /^\s*(?:(?:ok|so|and|but)[\s,]+)*(?:if i|what if|in what|where|why|will (?:my|it|the)|would (?:my|it|the)|does|is it|is there)\b/i.test(t)) && !/^\s*(?:can|could|would) (?:you|u)\b/i.test(t)) {
            var said = ''; try { said = B() && B().readAs ? B().readAs(steps) : ''; } catch (e) {}
            return { text: 'That sounds like a question, so nothing was changed.' + (said ? ' If you want this change, tap it: ' + said + '.' : ''), chips: ['Do it: ' + t.replace(/\?+\s*$/, '')] };
        }
        return null;
    }
    function onRoute(text, env, r) {
        var m = mode(); if (m === 'off' || !r) return r;
        if (env && !env.inConvo) FOCUS = null;          // a new chat: no focus carried over
        try { PREVF = FOCUS ? JSON.parse(JSON.stringify(FOCUS)) : null; } catch (ePF) { PREVF = null; }          // HELPER V3 S3 2026-10-06
        var pl = PEND; PEND = null;
        if (pl && m === 'enforce' && env && env.inConvo && Date.now() - pl.t < 600000) {          // the answer to my own "what should be red?": "the sides" / "the whole thing" -> "make the sides red"
            var tx = String(text || ''), rd0 = null; try { rd0 = IF().read(tx, env); } catch (e0) {}
            var wh0 = /\b(?:whole|wjole|hole|entire|every ?thing|all of it)\b/i.test(tx) || (rd0 && rd0.whole);
            if (rd0 && (wh0 || rd0.parts.length) && !COLW.concat(['chrome', 'carbon', 'matte', 'satin', 'gloss', 'candy', 'metallic']).some(function (c) { return new RegExp('\\b' + c + '\\b', 'i').test(tx); })) {
                var tgt = wh0 ? 'the whole car' : tx.replace(/^\s*(?:(?:no|nah|wait|only|just|ok|okay|actually|then|and|so|um+)[\s,.!]+)+/i, '').replace(/[.!?]+$/, '').trim();
                var OA = W.SpbOfflineAnswer, say2 = pl.said ? pl.text.replace(new RegExp('(?:the\\s+)?' + pl.said.replace(/[^a-z0-9 ]/gi, '.'), 'i'), tgt) : 'Make ' + tgt + ' ' + pl.look; if (tgt && OA && OA.route) { var r2 = null; try { r2 = OA.route(say2, env); } catch (e1) {} if (r2 && r2.cls === 'DO' && (r2.steps || []).length) { r2.v3 = logV({ stage: 'A', mode: m, verdict: 'repair', findings: [{ code: 'answered', what: say2.slice(0, 60) }], producer: 'offline' }); return r2; } }
            }
        }
        if (pl && !PEND && pl.ttl > 1 && !(r.cls === 'DO' && (r.steps || []).length)) { pl.ttl--; PEND = pl; }
        var st0 = r.steps || [];
        if (!st0.length || r.cls !== 'DO' || r.pass) { try { remember(IF().read(text, env), [], env); } catch (e) {} return r; }
        if (m === 'enforce' && !SWAPPING) { var sw = swapInLayer(text, env, st0); if (sw) return sw; }
        var p = null; try { p = plan(text, env, st0); } catch (e) { return r; }
        var qa = null; try { qa = questionAsk(text, p.rd, st0); } catch (e2) {}
        if (!qa && env && !env.inConvo && !env.last && BARE_RE.test(String(text)) && st0.some(function (s0) { var t0 = touchOf(s0, env); return t0.k === 'body'; })) {
            var lk = String(text).trim().replace(/[.!]+$/, '').replace(/^(?:make (?:it|her)|go|do it|paint it)\s+/i, '').toLowerCase();
            PEND = { look: lk, t: Date.now(), ttl: 2 };
            qa = { text: 'What should be ' + lk + '? Nothing was changed yet. Tap one, or name a part.', chips: ['Make the whole car ' + lk, 'Make the hood ' + lk, 'Make the roof ' + lk, 'Make the sides ' + lk] };
        }
        if (qa) p.fx.push({ code: 'question', what: String(text).slice(0, 60) });
        var verdict = !p.fx.length ? 'ok' : (qa || p.ask || !p.steps.filter(function (s) { return s.what && s.what.k !== 'step'; }).length) ? 'ask' : 'repair';
        var v = logV({ stage: 'A', mode: m, verdict: verdict, findings: p.fx.slice(0, 6), producer: 'offline' });
        if (m === 'warn' || verdict === 'ok') { r.v3 = v; try { remember(p.rd, st0, env); } catch (e3) {} return r; }
        if (verdict === 'ask') {
            var q = qa || p.ask || { text: 'You asked to keep that as it is, so there is nothing left to change. What should change?', chips: [] };
            if (!qa && p.ask && p.ask.pendWhich && p.said) PEND = { said: p.said, text: String(text), t: Date.now(), ttl: 2 };
            var out = askResult(r, q, qa ? 'question' : 'scope'); out.v3 = v; if (qa && p.rd.parts.length) out.pend = { need: 'value', parts: p.rd.parts.slice() };          /* "two options for the hood: carbon or satin" -> "carbon" answers it */
            try { remember(p.rd, [], env); } catch (e4) {} return out;
        }
        r.steps = p.steps; r.v3 = v;
        if (p.notes.length && r.steps[0]) r.steps[0].note = (r.steps[0].note ? r.steps[0].note + ' ' : '') + p.notes.join(' ');
        try { remember(p.rd, r.steps, env); } catch (e5) {}
        return r;
    }

    // ------------------------------------------------------------------ stage A, measured: the app queue (offline Run, DeepSeek, MCP) vs the sentence + the decal layers
    function onQueue(queue, o) {
        o = o || {}; var m = mode(); if (m === 'off' || !queue || !queue.length) return null;
        var Z = W.SpbProZone, F = IF(); if (!Z || !Z.probeRegion || !F) return null;
        var env = { layers: [] }; try { var C = W.SpbProCar, rl = C && C.roles ? C.roles() : []; env.layers = rl.map(function (x) { return { name: x.name, role: x.role }; }); } catch (e) {}
        var text = o.mcp ? '' : String(o.text || ''), rd = F.read(text, env), fx = [], failed = [], out = [];
        var decal = env.layers.filter(function (l) { var r0 = layerRole(l.name, env); return r0 === 'numbers' || r0 === 'sponsors'; }).map(function (l) { return l.name; });
        // "make everything black but keep the skull colorful": a kept thing that is not a car part (art, a logo, the skull) lives on the decal / art layers,
        // so "everything" means the body paint here (the app's own "everything = decals too" reading would paint the skull over: in-app bank A-0374)
        var objKeep = null, km = /\b(?:keep(?:ing)?|leave|leaving|but not|except(?: for)?|without touching|apart from|other than)\s+(?:the |my |our |that |this )?([a-z]+)/i.exec(text);
        if (km && !/^(?:hood|roof|trunk|spoiler|bumpers?|sides?|doors?|side|front|rear|back|left|right|car|body|base|rest|colou?rs?|same|it|them|everything|paint|shine|finish)$/i.test(km[1]) && COLW.indexOf(km[1].toLowerCase()) === -1) objKeep = km[1];
        var bodyL = env.layers.filter(function (l) { return layerRole(l.name, env) === 'body'; }).map(function (l) { return l.name; });
        // HELPER V3 S3 2026-10-06: a follow-up that names nothing new ("reduce the chrome 50%, more metallic gold" after "In the Numbers layer: gold chrome", bank A-0284)
        // refines the LAST change: the decal layers that change already touched are named by the conversation (the store, js/spb-convo-state.js)
        var prevL = []; try { var CVq = W.SpbConvo; if (!o.mcp && CVq && CVq.wired() && !rd.parts.length && !rd.layers.length && !rd.elements.length && !rd.whole) { var lc = CVq.changes().filter(function (c) { return !c.undone; }).pop(); if (lc && lc.layers) prevL = lc.layers.slice(); } if (!o.mcp && PREVF && !rd.parts.length && !rd.layers.length && !rd.elements.length && !rd.whole) prevL = prevL.concat(PREVF.layers || []); } catch (ePL) {}          // + the focus the chat had BEFORE this sentence ("Logos layer: chroome" -> ask -> "no, silver, brushed", bank A-0236)
        try { var C2 = W.SpbProCar, rl2 = C2 && C2.roles ? C2.roles() : []; var bl2 = rl2.filter(function (x) { return x.role === 'body paint' && x.visible; }).map(function (x) { return x.name; }); if (bl2.length) bodyL = bl2; } catch (eB) {}
        queue.forEach(function (q) {
            var sp = q && q.spec, rg = sp && sp.region;
            if (objKeep && !o.mcp && rg && (rg.everything || rg.remaining) && !(rg.layers && rg.layers.length) && !rg.colors && !rg.island && !rg.part && bodyL.length && (q.kind === 'add' || q.kind === 'edit')) {
                fx.push({ code: 'kept-object', what: objKeep + ' (whole car -> body paint layers)', zone: sp.name || null });
                if (m === 'enforce') { q = clone(q); delete q.spec.region.everything; delete q.spec.region.remaining; q.spec.region.layers = bodyL.slice(); sp = q.spec; rg = sp.region; }
            } if (!rg || !(q.kind === 'add' || q.kind === 'edit') || rg.rect || rg.cells || rg.graphic) { out.push(q); return; }
            // decal layers the request did not name
            var ls = [].concat(rg.layers || []), bad = ls.filter(function (l) { return decal.indexOf(l) !== -1 && !o.mcp && rd.decals !== 'include' && rd.layers.indexOf(l) === -1 && rd.elements.indexOf(layerRole(l, env)) === -1 && prevL.indexOf(l) === -1; });
            if (bad.length) {
                fx.push({ code: 'decal', what: bad.join('+'), zone: sp.name || null });
                if (m === 'enforce') { var keepL = ls.filter(function (l) { return bad.indexOf(l) === -1; }); if (!keepL.length) { failed.push((sp.name || 'a zone') + ': not done, it would have changed ' + bad.join(', ') + ' (numbers / logos / decals you did not name)'); return; } q = clone(q); q.spec.region.layers = keepL; rg = q.spec.region; }
            }
            // named parts (no whole-car words): nothing outside them
            if (!o.mcp && rd.parts.length && !rd.whole && !/\b(?:body|base|livery|scheme|car|every ?thing|rest|stripes?|graphics?|design)\b/i.test(text) && !rd.keep.parts.length) {          // a livery sentence ("white body, red hood") has a whole-car base on purpose
                var probe = clone(rg); if (probe.part) { probe.island = probe.part; delete probe.part; } probe.exclude = [].concat(probe.exclude || []).concat(rd.parts);
                var pr = null; try { pr = Z.probeRegion(probe); } catch (e2) {} var sh = pr && pr.share_pct != null ? Number(pr.share_pct) : 0;
                if (sh > 1) {
                    fx.push({ code: 'outside', what: Math.round(sh * 10) / 10 + '% outside the ' + rd.parts.join('+'), zone: sp.name || null, outside_pct: sh });
                    if (m === 'enforce') {
                        var rp = clone(rg);
                        if (!rp.island && !rp.part) rp.island = rd.parts.length === 1 ? rd.parts[0] : rd.parts.slice();
                        var pr2 = null, chk = clone(rp); if (chk.part) { chk.island = chk.part; delete chk.part; } chk.exclude = [].concat(chk.exclude || []).concat(rd.parts); try { pr2 = Z.probeRegion(chk); } catch (e3) {}
                        if (pr2 && Number(pr2.share_pct || 0) <= 1) { q = clone(q); q.spec.region = rp; }
                        else { failed.push((sp.name || 'a zone') + ': not done, it would also change about ' + Math.round(sh) + '% of the car outside the ' + rd.parts.join(' and ')); return; }
                    }
                }
            }
            // kept parts: cut them out
            if (!o.mcp && rd.keep.parts.length) {
                var pk = null, pq = clone(rg); if (pq.part) { pq.island = pq.part; delete pq.part; } try { pk = Z.probeRegion(Object.assign({}, pq, { island: rd.keep.parts.length === 1 ? rd.keep.parts[0] : rd.keep.parts.slice() })); } catch (e4) {}
                var inKept = pk && !pk.note && Number(pk.share_pct || 0) > 0.5 && !pq.island;
                if (inKept && [].concat(pq.exclude || []).filter(function (x) { return rd.keep.parts.indexOf(x) !== -1; }).length < rd.keep.parts.length) {
                    fx.push({ code: 'kept-exclude', what: rd.keep.parts.join('+'), zone: sp.name || null });
                    if (m === 'enforce') { q = clone(q); q.spec.region.exclude = uniq([].concat(q.spec.region.exclude || []).concat(rd.keep.parts)); }
                }
            }
            out.push(q);
        });
        var v = logV({ stage: 'A-mask', mode: m, verdict: !fx.length ? 'ok' : (m === 'warn' ? 'warn' : (failed.length ? (out.length ? 'repair' : 'ask') : 'repair')), findings: fx.slice(0, 6), producer: o.producer || (o.mcp ? 'mcp' : 'app') });
        if (fx.length) { try { var lf = F.last(); if (lf && Date.now() - (lf.t || 0) < 60000) lf.verify_mask = v; } catch (e5) {} }
        if (m !== 'enforce' || !fx.length) return { queue: queue, failed: [], v: v };
        return { queue: out, failed: failed, v: v };
    }

    W.SpbIntentVerify = { mode: mode, onRoute: onRoute, onQueue: onQueue, plan: plan, since: function (t0) { return LOG.filter(function (v) { return (v.t || 0) >= (t0 || 0); }); }, _focus: function () { return FOCUS; }, _reset: function () { PREVF = null; FOCUS = null; PEND = null; LOG = []; return true; } };
})();
