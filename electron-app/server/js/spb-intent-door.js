/* ============================================================================
   spb-intent-door.js - D-DOOR 2026-10-08: sub-part words of a side panel -> the region the buyer means
   "paint the door red", "flames from the front fender to the door", "number on the door", "rear quarter panel black", "both doors", "rocker panels gunmetal"
   used to recolour the WHOLE side (the intent layer knew only 'left side' / 'right side'). annotate(frame, text, env) rewrites the frame's side-panel targets:
       { kind:'part', parts:['left side'] }  ->  { kind:'part', parts:['left side'], portion:'door' }      (= the notation 'left side@door')
   portion tokens: 'door' | 'front fender' | 'rear quarter' | 'rocker' | '<a> to <b>' (a span in nose->tail order: 'front fender to door', 'door to rear quarter').
   The region itself (fractions along the panel's nose->tail axis, wheel arches measured from the panel mask, nose end = ONE data field per car in js/spb-door-data.js) lives in
   js/spb-pro-carmap.js (SpbProCar.subStatus / maskFor(ref, portion)). When the car map cannot say where the area is (nose end unconfirmed, no measurable panel) the frame becomes an
   ASK ("type or circle the area"), never a whole-side paint.
   Called from SpbIntentFrame.routeToFrame (regex reader), SpbIntentOfflineFrame.frameOf (kNN reader) and SpbIntentModel (AI / MCP frames). ES5.
   Kill switch: window.SPB_DOOR_OFF = true (also localStorage SPB_DOOR_OFF = '1').
   ============================================================================ */
(function (root) {
    'use strict';
    var W = root || {};
    function off() { try { if (W.SPB_DOOR_OFF) return true; if (W.localStorage && W.localStorage.getItem('SPB_DOOR_OFF') === '1') return true; } catch (e) {} return false; }
    function low(t) { return String(t || '').toLowerCase().replace(/[‘’]/g, "'"); }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    var SIDES = ['left side', 'right side'];
    // one sub-part word, with an optional left/right qualifier in front of it ("the left front door", "passenger side fender")
    var MENTION = /(?:\b(left|right|driver'?s?|passenger'?s?|lhs|rhs)(?:[- ]hand)?\s+(?:side\s+)?(?:front\s+|rear\s+|back\s+)?)?\b(front fenders?|rear fenders?|back fenders?|fenders?|rear quarter ?panels?|rear quarters?|back quarters?|quarter ?panels?|quarters?|doors?|rocker ?panels?|rockers?|side ?skirts?|skirts?|sills?)\b/g;
    var SIZE_BEFORE = /(?:\b(?:lower|upper|top|bottom|first|last|a|one|per|front|half|third)\s+|\b1\/4\s*)$/;          // "lower quarter", "a quarter of", "front quarter": a size, not the panel
    var SIZE_AFTER = /^\s*(?:of\b|inch|in\b|size|\d)/;
    var DOOR_NOT = /^\s*(?:handles?|mirrors?|windows?|glass|jambs?|locks?|gaps?|seals?|sills? plates?)\b/;
    function kindOf(w) {
        w = w.replace(/\s+/g, ' ').replace(/s$/, '');
        if (/^(?:rear|back) fender|quarter/.test(w)) return 'quarter';
        if (/fender/.test(w)) return 'fender';
        if (/door/.test(w)) return 'door';
        return 'rocker';
    }
    function sideOf(q) { if (!q) return null; if (/^(?:left|lhs|driver)/.test(q)) return 'left side'; if (/^(?:right|rhs|passenger)/.test(q)) return 'right side'; return null; }
    function mentions(text) {
        var s = low(text), out = [], m; MENTION.lastIndex = 0;
        while ((m = MENTION.exec(s))) {
            var word = m[2], before = s.slice(0, m.index), after = s.slice(m.index + m[0].length), k = kindOf(word);
            if (k === 'quarter' && !/rear|back/.test(word) && (SIZE_BEFORE.test(before) || SIZE_AFTER.test(after))) continue;
            if (k === 'quarter' && /rear|back/.test(word) && SIZE_AFTER.test(after) && /^\s*of\b/.test(after)) continue;          // "the rear quarter of the hood"
            if (k === 'door' && DOOR_NOT.test(after)) continue;
            var both = /\b(?:both|two|all|each|every)\s+(?:the\s+)?(?:\w+\s+)?$/.test(before.slice(-20));
            out.push({ kind: k, side: sideOf(m[1]), start: m.index, end: m.index + m[0].length, plural: both, wordStart: m.index + m[0].length - word.length });
        }
        return out;
    }
    var NAME = { fender: 'front fender', door: 'door', quarter: 'rear quarter', rocker: 'rocker' };
    var ORDER = { fender: 0, door: 1, quarter: 2 };
    var SPAN_TO = /^\s*(?:[,;]\s*)?(?:to|through|thru|till|until|into|up to|all the way (?:to|through|up to|back to)|right (?:up )?to|and into|and onto|onto|over to)\s+(?:the\s+)?(?:\w+\s+)?$/;
    var SPAN_AND = /^\s*(?:[,;&+]|and|plus|then|as well as|along with)?\s*(?:and\s+)?(?:the\s+)?(?:\w+\s+)?$/;
    // sub-part mentions -> groups [{ portion, side }]; "front fender to door" is one group (a span), "door and rear quarter" (adjacent) too, "fender and quarter" are two
    function groups(text) {
        var s = low(text), ms = mentions(s), g = [], i = 0;
        while (i < ms.length) {
            var a = ms[i], b = ms[i + 1];
            if (b && a.kind !== 'rocker' && b.kind !== 'rocker' && a.kind !== b.kind && (a.side === b.side || !a.side || !b.side)) {
                var gap = s.slice(a.end, b.wordStart), isTo = SPAN_TO.test(gap), isAnd = !isTo && gap.length <= 14 && SPAN_AND.test(gap) && Math.abs(ORDER[a.kind] - ORDER[b.kind]) === 1;
                if (isTo || isAnd) { var lo = ORDER[a.kind] <= ORDER[b.kind] ? a : b, hi = lo === a ? b : a; g.push({ portion: NAME[lo.kind] + ' to ' + NAME[hi.kind], side: a.side || b.side, plural: a.plural || b.plural, at: Math.min(a.wordStart, b.wordStart) }); i += 2; continue; }
            }
            g.push({ portion: NAME[a.kind], side: a.side, plural: a.plural, at: a.wordStart }); i++;
        }
        return g;
    }
    function sideOnly(parts) { return parts && parts.length && parts.every(function (p) { return SIDES.indexOf(p) >= 0; }); }
    function hasSide(parts) { return (parts || []).some(function (p) { return SIDES.indexOf(p) >= 0; }); }
    var KINDS = { part: 1, layer: 1, element: 1, graphic: 1 };
    function candidate(op) { var T = op && op.target; return !!(T && KINDS[T.kind] && T.parts && hasSide(T.parts) && (!T.portion || /^(?:rear|front) quarter$/.test(String(T.portion)))); }
    function status(sideParts, portion) {
        var C = W.SpbProCar; if (!C || typeof C.subStatus !== 'function') return { ok: true, unchecked: true };
        for (var i = 0; i < sideParts.length; i++) { var st = null; try { st = C.subStatus(sideParts[i], portion); } catch (e) { st = null; } if (st && st.ok === false) return st; }
        return { ok: true };
    }
    // frame, text -> { changed, asked, groups }
    function annotate(frame, text, env) {
        var res = { changed: false, asked: false, groups: [] };
        try {
            if (off() || !frame || frame.act !== 'change' || !(frame.ops || []).length) return res;
            var gs = groups(text); if (!gs.length) return res; res.groups = gs; begin(gs, text);
            var ops = frame.ops, cand = [], i;
            for (i = 0; i < ops.length; i++) if (candidate(ops[i])) cand.push(i);
            if (!cand.length) return res;
            // bind groups to ops: one group = every side op; n groups over n ops = in order; n groups over one op = clone per group; anything else = leave as it was (the planner's own reading)
            var plan = [];          // [{ opIndex, group }]
            if (gs.length === 1) cand.forEach(function (ci) { plan.push({ oi: ci, g: gs[0] }); });
            else if (gs.length === cand.length) cand.forEach(function (ci, k) { plan.push({ oi: ci, g: gs[k] }); });
            else if (cand.length === 1) gs.forEach(function (g) { plan.push({ oi: cand[0], g: g }); });
            else return res;
            // check the car map can place every area BEFORE touching the frame
            for (i = 0; i < plan.length; i++) {
                var T0 = ops[plan[i].oi].target, sp = T0.parts.filter(function (p) { return SIDES.indexOf(p) >= 0; }); if (plan[i].g.side && sp.indexOf(plan[i].g.side) >= 0) sp = [plan[i].g.side];
                var st = status(sp, plan[i].g.portion);
                if (!st.ok) { frame.act = 'ask_back'; frame.missing = ['target']; frame.question = st.ask || ('I cannot place the ' + plan[i].g.portion + ' on this car. Type or circle the area.'); frame.ops = []; frame.door = { asked: true, why: st.why || null, portion: plan[i].g.portion }; res.asked = true; return res; }
            }
            var out = [], used = {};
            for (i = 0; i < ops.length; i++) {
                var mine = plan.filter(function (p) { return p.oi === i; });
                if (!mine.length) { out.push(ops[i]); continue; }
                mine.forEach(function (p, k) {
                    var o = k === 0 ? ops[i] : clone(ops[i]), T = o.target, sidesIn = T.parts.filter(function (x) { return SIDES.indexOf(x) >= 0; }), rest = T.parts.filter(function (x) { return SIDES.indexOf(x) < 0; });
                    var sd = (p.g.side && sidesIn.indexOf(p.g.side) >= 0) ? [p.g.side] : sidesIn;
                    if (rest.length && k === 0 && mine.length === 1) { var oR = clone(ops[i]); oR.target.parts = rest.slice(); delete oR.target.portion; T.parts = sd.slice(); T.portion = p.g.portion; o.door = p.g.portion; out.push(o); out.push(oR); res.changed = true; return; }
                    T.parts = sd.concat(rest); T.portion = p.g.portion; o.door = p.g.portion; out.push(o); res.changed = true;
                });
            }
            if (res.changed) { frame.ops = out; frame.door = { portions: plan.map(function (p) { return p.g.portion; }) }; }
        } catch (e) { res.error = String(e && e.message || e); }
        return res;
    }

    // pro-edit.js (the offline helper's edit reader) hook: its target hits [{kind:'part', part:'left side', at}] -> 'left side@door' hits; { hits, ask }
    function editParts(rest, hits) {
        try {
            if (off()) return { hits: hits };
            var gs = groups(rest); if (!gs.length) return { hits: hits }; begin(gs, rest);
            var sideHits = hits.filter(function (h) { return h && h.kind === 'part' && SIDES.indexOf(h.part) >= 0; }), others = hits.filter(function (h) { return !(h && h.kind === 'part' && SIDES.indexOf(h.part) >= 0); }), out = [], ask = null, fromHits = [];
            sideHits.forEach(function (h) { if (fromHits.indexOf(h.part) < 0) fromHits.push(h.part); });
            gs.forEach(function (g) {
                var sides = g.side ? [g.side] : (fromHits.length ? fromHits : SIDES.slice()), st = status(sides, g.portion);
                if (!st.ok && !ask) ask = st.ask || ('I cannot place the ' + g.portion + ' on this car. Type or circle the area.');
                sides.forEach(function (sd) { out.push({ kind: 'part', part: sd + '@' + g.portion, at: g.at }); });
            });
            return { hits: others.concat(out), ask: ask, groups: gs };
        } catch (e) { return { hits: hits }; }
    }

    // ---- CTXZ: the central net. Whatever path builds the zones (planner, offline answer, edit reader, tell reader), a zone whose region is a WHOLE side panel
    // while the buyer's latest sentence named a door / fender / quarter / rocker gets that portion (the car map resolves it, or returns an EMPTY mask when it cannot: never the whole side).
    var CTX = null, ARMED = false, TRIES = 0;
    function begin(gs, text) { if (CTX && CTX.full && Date.now() - CTX.t < 120000) return; CTX = { groups: gs, t: Date.now(), text: String(text || '').slice(0, 160) }; arm(); }
    function beginFull(text) { try { var gs = off() ? [] : groups(text); CTX = gs.length ? { groups: gs, t: Date.now(), text: String(text || '').slice(0, 160), full: true } : null; } catch (e) { CTX = null; } }
    function live() { return (CTX && !off() && Date.now() - CTX.t < 120000) ? CTX : null; }
    function plain(r) { return r && r.island && !r.portion && !r.band && !r.rect && !r.cells && !r.part && !r.element && !r.graphic && !r.everything && !r.remaining; }
    function islandsOf(r) { return [].concat(r.island); }
    function bind(r, ctx, nth, total) {
        var isl = islandsOf(r); if (!isl.length || !isl.every(function (x) { return SIDES.indexOf(x) >= 0; })) return null;
        var cand = ctx.groups.filter(function (g) { return !g.side || isl.every(function (x) { return x === g.side; }); });
        if (!cand.length) return null;
        var g = cand.length === 1 ? cand[0] : (total === cand.length ? cand[Math.min(nth, cand.length - 1)] : cand[0]);
        return g.portion;
    }
    function fixSpecs(specs) {          // specs: [{ spec, edit:zone|null }]
        var ctx = live(); if (!ctx) return;
        var hits = specs.filter(function (x) { return x.spec && x.spec.region && plain(x.spec.region) && islandsOf(x.spec.region).every(function (i) { return SIDES.indexOf(i) >= 0; }); });
        var blocked = null;
        hits.forEach(function (x, n) { var por = bind(x.spec.region, ctx, n, hits.length); if (por) { x.spec.region.portion = por; x.spec.region._door = por; if (!blocked) { var st = status(islandsOf(x.spec.region), por); if (!st.ok) blocked = st.ask || ('I cannot place the ' + por + ' on this car. Type or circle the area.'); } } });
        return blocked;
    }
    function wholeSideZone(z) { try { return z && z.regionMask && z.useRegion && /^(?:left side|right side)(?: \+ (?:left side|right side))?$/.test(String(z._regionDesc || '').replace(/^kept to /, '')); } catch (e) { return false; } }
    // the sentence names a door / fender / quarter / rocker and the car map cannot place it on a side it would touch -> the ask text (never a paint job on the whole side, never a half-done one)
    function preAsk(text) {
        if (off()) return null; var gs = groups(text); if (!gs.length) return null;
        var low0 = low(text), named = /\b(?:left|driver|lhs)\b/.test(low0) ? 'left side' : (/\b(?:right|passenger|rhs)\b/.test(low0) ? 'right side' : null);
        for (var i = 0; i < gs.length; i++) { var sides = gs[i].side ? [gs[i].side] : (named && !/\bboth\b/.test(low0) ? [named] : SIDES.slice()), st = status(sides, gs[i].portion); if (!st.ok) return st.ask || ('I cannot place the ' + gs[i].portion + ' on this car. Type or circle the area.'); }
        return null;
    }
    var RT = 0;
    function armReaders() {          // the full sentence, once per request, from the two readers every typed request passes through (loaded after this file: retry)
        var Ed = W.SpbProEdit, OAw = W.SpbOfflineAnswer, need = false;
        if (Ed && Ed.plan) { if (!Ed.plan.__dd) { var op0 = Ed.plan; Ed.plan = function (t) { try { beginFull(t); var pa = preAsk(t); if (pa) return { kind: 'ask', text: pa, chips: [] }; } catch (e) {} return op0.apply(this, arguments); }; Ed.plan.__dd = 1; } } else need = true;
        if (OAw && OAw.route) { if (!OAw.route.__dd) { var or0 = OAw.route; OAw.route = function (t) { try { beginFull(t); var pa = preAsk(t); if (pa) return { cls: 'ASK', steps: [], ask: { text: pa, chips: [] }, via: 'door', why: 'door-ask', said: String(t || '').slice(0, 160), door: { asked: true } }; } catch (e) {} return or0.apply(this, arguments); }; OAw.route.__dd = 1; } } else need = true;
        if (need && typeof document !== 'undefined' && ++RT < 80) setTimeout(armReaders, 1000);
    }

    var APPEAR = ['color', 'finish', 'base', 'pattern', 'intensity', 'rel', 'shade', 'gradient', 'colors_by'];
    function zoneList() { try { return typeof zones !== 'undefined' ? zones : (W.zones || null); } catch (e) { return null; } }
    function sidesOfDesc(d) { var o = [], m, re = /(left|right) side/g; d = String(d || ''); while ((m = re.exec(d))) if (o.indexOf(m[0]) < 0) o.push(m[0]); return o; }
    // an EDIT of a zone that paints a whole side ("make the left door blue" after "paint the left side red") must not recolour the whole side: it becomes a new door zone on top that copies the look
    function editToAdd(zref, spec) {
        try {
            var ctx = live(); if (!ctx || !spec || spec.region != null) return null;
            var L = zoneList(), z = (zref && typeof zref === 'object') ? zref : (L ? L[zref] : null); if (!z || !wholeSideZone(z)) return null;
            var any = false; APPEAR.forEach(function (k) { if (spec[k] != null) any = true; }); if (!any) return null;
            var sides = sidesOfDesc(z._regionDesc); if (!sides.length) return null;
            var isl = sides.length > 1 ? sides : sides[0], r = { island: isl };
            var por = bind(r, ctx, 0, 1); if (!por) return null;
            var add = {}; Object.keys(spec).forEach(function (k) { add[k] = spec[k]; });
            var lay = (z.sourceLayers && z.sourceLayers.length) ? z.sourceLayers.slice() : null;
            r.portion = por; r._door = por; if (lay) r.layers = lay;
            add.region = r; add.copy_look_from = z; add.name = spec.name || ((String(z.name || 'zone').replace(/ (?:left|right) side.*$/i, '') + ' ' + sides.join(' + ').replace(/ side/g, '') + ' ' + por).trim());
            if (add.color == null && z.baseColorMode === 'solid' && z.baseColor) add.color = z.baseColor;
            return add;
        } catch (e) { return null; }
    }
    function arm() {
        if (ARMED || typeof document === 'undefined') return; var Z = W.SpbProZone; if (!Z || !Z.batch || Z.batch.__dd) { if (!Z && ++TRIES < 60) setTimeout(arm, 1000); return; }
        try {
            var ob = Z.batch, oa = Z.add, oe = Z.edit;
            Z.batch = function (ops, label, opts) { try { if (live() && ops && ops.length) { var sp = []; for (var oi = 0; oi < ops.length; oi++) { var o0 = ops[oi]; if (o0 && o0.kind === 'edit' && o0.spec) { var ad = editToAdd(o0.zone, o0.spec); if (ad) ops[oi] = { kind: 'add', spec: ad }; } } ops.forEach(function (o) { if (o && o.kind === 'add' && o.spec) sp.push({ spec: o.spec }); }); var bk = fixSpecs(sp); if (bk) return ops.map(function (o) { return { ok: false, applied: [], warnings: [bk], error: bk, index: -1, name: o && o.spec && o.spec.name }; }); } } catch (e) {} return ob.apply(this, arguments); };
            Z.add = function (s) { try { if (live() && s) { var bk = fixSpecs([{ spec: s }]); if (bk) return { ok: false, applied: [], warnings: [bk], error: bk }; } } catch (e) {} return oa.apply(this, arguments); };
            if (oe) { Z.edit = function (t, sp) { try { if (live()) { var ad = editToAdd(t, sp); if (ad) return Z.add(ad); } } catch (e) {} return oe.apply(this, arguments); }; Z.edit.__dd = 1; }
            Z.batch.__dd = 1; Z.add.__dd = 1; ARMED = true;
            armReaders();
        } catch (e) {}
    }
    arm();
    var api = { ctx: function () { return CTX; }, begin: begin, editParts: editParts, annotate: annotate, groups: groups, mentions: mentions, off: off, V: 1 };
    W.SpbIntentDoor = api;
    if (typeof module === 'object' && module && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
