/* ============================================================================
   SPB EASY TELL v2 — "Tell Shokker what you want"  (SPB-EASY-TELL2 2026-09-30)
   A command bar at the top of the Easy stage. Type (or tap an idea) in plain English:

       make the numbers white chrome            everything matte except the sponsors
       the cyan candy, the yellow gold          make it look expensive        surprise me

   It shows what it understood WHILE you type, does it when you press Enter, and leaves a receipt
   with UNDO and ◀ ▶ "try another finish". Follow-ups work: "darker", "bigger flakes", "more", "another".

   NO LLM, no network. The language brain is js/spb-easy-tell-nlu.js (pure logic, tested under Node against the
   real catalog + the real car). This file is only the view + the executor: it turns a parsed plan into calls on
   window.spbEasyAuto (batch / recolor / apply / blend / adjust / layerPart / look / undo).
   Contract used: parts layers layerPart apply recolor blend adjust partState batch look undo redo historyTop selected
   lastPart hover hoverLayer unhover search sections finishInfo thumb toast onRail startOver open
   Isolation law: nothing here writes Pro's zones directly; every change goes through the Easy API.
   ES5 only (old Electron). Nothing is position:fixed; the dock lives inside #spbEasyProof.
   ========================================================================== */
(function () {
    'use strict';
    var NLU = window.SpbTellNLU;
    if (!NLU) { try { console.warn('[EASY TELL] language engine missing'); } catch (e) {} return; }

    // ------------------------------------------------------------ utilities
    function $(id) { return document.getElementById(id); }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function A() { return window.spbEasyAuto || null; }
    function toast(msg) { var a = A(); try { if (a && a.toast) a.toast(msg); } catch (e) {} }
    function isHex(s) { return /^#[0-9a-f]{6}$/i.test(String(s || '')); }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

    // ------------------------------------------------------------ state
    var S = {
        phrase: '', plan: null, planFor: null, feed: [], last: null, lastRecipe: null, uid: 0, seed: Math.floor(Math.random() * 6),
        pending: null,            // a plan waiting for the buyer to say WHICH part
        confirmStart: false, comps: [], help: false, paintKey: null, hist: [], histAt: -1, focus: false, tip: 0, showAlts: null
    };
    var _dock = null, _input = null, _timer = null, _tipTimer = null, _flashTimer = null;

    // ------------------------------------------------------------ catalog index (lazy, rebuilt if the catalog grows)
    var _ix = null, _ixN = -1;
    function catalogCount() {
        var n = 0;
        try { n += Object.keys(typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID ? BASES_BY_ID : {}).length; } catch (e) {}
        try { n += Object.keys(typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID ? MONOLITHICS_BY_ID : {}).length; } catch (e2) {}
        return n;
    }
    function index() {
        var a = A(), n = catalogCount();
        if (_ix && _ixN === n) return _ix;
        var fin = [];
        function scan(map, type) {
            if (typeof map === 'undefined' || !map) return;
            Object.keys(map).forEach(function (id) {
                try { if (type === 'base' && typeof spbResolveBaseId === 'function' && spbResolveBaseId(id) !== id) return; } catch (e) {}   // retired alias ids
                var m = map[id] || {};
                fin.push({ key: type + '::' + id, id: id, type: type, name: String(m.name || id), desc: String(m.desc || '') });
            });
        }
        try { scan(typeof BASES_BY_ID !== 'undefined' ? BASES_BY_ID : null, 'base'); } catch (e3) {}
        try { scan(typeof MONOLITHICS_BY_ID !== 'undefined' ? MONOLITHICS_BY_ID : null, 'monolithic'); } catch (e4) {}
        var secs = [], top = [];
        try { secs = (a.sections() || []).map(function (s) { return { title: s.title, keys: s.ids || s.keys || [] }; }); } catch (e5) {}
        try { top = a.search('') || []; } catch (e6) {}
        _ix = NLU.buildIndex({ finishes: fin, sections: secs, top: top });
        _ixN = n;
        return _ix;
    }
    function world() {
        var a = A(), sel = -1;
        try { sel = a.selected(); if (sel < 0 && !S.last) sel = a.lastPart(); } catch (e) {}
        return { parts: a.parts(), layers: a.layers(), index: index(), ctx: { selected: sel, last: S.last, lastRecipe: S.lastRecipe } };
    }
    function ready() {
        var a = A(); if (!a) return false;
        try { return document.body.classList.contains('spb-easy-on') && document.body.classList.contains('spb-easy-auto-view') && a.parts().length > 0; } catch (e) { return false; }
    }
    function finInfo(key) { var a = A(); try { return a && key ? a.finishInfo(key) : null; } catch (e) { return null; } }
    function thumb(key) { var a = A(); try { return a && a.thumb ? a.thumb(key) : ''; } catch (e) { return ''; } }

    // ------------------------------------------------------------ resolving targets to live part indexes
    function partsNow() { var a = A(); try { return a.parts(); } catch (e) { return []; } }
    function idxOfLayer(layerId, create) {
        var ps = partsNow(), i;
        for (i = 0; i < ps.length; i++) if (ps[i].layerId === layerId && ps[i].kind === 'layer') return ps[i].idx;
        if (!create) return -1;
        try { return A().layerPart(layerId); } catch (e) { return -1; }
    }
    function targetIdxs(cmd, create) {
        var ps = partsNow(), out = [], seen = {}, ex = {}, exLayer = {}, i;
        function add(idx) { if (idx != null && idx >= 0 && !seen[idx]) { seen[idx] = 1; out.push(idx); } }
        (cmd.exclude || []).forEach(function (t) { if (t.kind === 'part') ex[t.idx] = 1; else if (t.kind === 'layer') { exLayer[t.layerId] = 1; var li = idxOfLayer(t.layerId, false); if (li >= 0) ex[li] = 1; } });
        (cmd.targets || []).forEach(function (t) {
            if (t.kind === 'part') { for (i = 0; i < ps.length; i++) if (ps[i].idx === t.idx) add(t.idx); }
            else if (t.kind === 'layer') add(idxOfLayer(t.layerId, create !== false));
            else if (t.kind === 'whole') ps.forEach(function (p) { if (p.kind !== 'layer') add(p.idx); });
            else if (t.kind === 'colors') ps.forEach(function (p) { if (NLU.isBodyColor(p)) add(p.idx); });
            else if (t.kind === 'layers') { var ls = []; try { ls = A().layers(); } catch (e) {} ls.forEach(function (l) { if (!exLayer[l.id]) add(idxOfLayer(l.id, create !== false)); }); }
        });
        return out.filter(function (idx) { return !ex[idx]; });
    }
    function labelOfIdx(idx) { var ps = partsNow(); for (var i = 0; i < ps.length; i++) if (ps[i].idx === idx) return ps[i].label || ps[i].name; return 'part'; }

    // ------------------------------------------------------------ executor
    function adjustOpts(cmd, st) {
        var o = {}, mulSize = 1, dHue = 0, dSat = 0, dBri = 0, blend = null, blendMoved = false;
        (cmd.adjusts || []).forEach(function (a) {
            var m = a.mag || 1;
            if (a.op === 'size') mulSize *= Math.pow(1.5, a.dir * m);
            else if (a.op === 'bri') dBri += a.dir * 25 * m;
            else if (a.op === 'sat') dSat += a.dir * 25 * m;
            else if (a.op === 'hue') dHue += a.dir * 30 * m;
            else if (a.op === 'dSat') dSat += a.value;                       // looks (vibes) carry exact steps
            else if (a.op === 'dBri') dBri += a.value;
            else if (a.op === 'dHue') dHue += a.value;
            else if (a.op === 'blend') { blend = clamp((blend == null ? st.blend : blend) + a.dir * 0.25 * m, 0, 1); }
            else if (a.op === 'blendTo') blend = clamp(a.value, 0, 1);
            else if (a.op === 'intensity') {
                var cur = blend == null ? st.blend : blend;
                if (a.dir > 0) { if (cur < 0.99) blend = clamp(cur + 0.25 * m, 0, 1); else dSat += 25 * m; }
                else { if (cur > 0.3) blend = clamp(cur - 0.25 * m, 0, 1); else dSat -= 25 * m; }
            }
        });
        if (mulSize !== 1) o.scaleMul = mulSize;
        if (dHue) o.dHue = dHue; if (dSat) o.dSat = dSat; if (dBri) o.dBri = dBri;
        if (blend != null) o.blend = blend;
        for (var k in o) if (o.hasOwnProperty(k)) return o;
        return null;
    }
    function execStyle(cmd, rec) {
        var a = A(), idxs = targetIdxs(cmd, true), res = { cmd: cmd, idxs: idxs, applied: 0, failed: 0 }, key = cmd.finish && cmd.finish.key, color = cmd.color || null;
        if (!idxs.length) { res.failed = 1; res.msg = 'Nothing to change there.'; return res; }
        if (cmd.how === 'shine' && key) {                                     // the whole-car lever: paint untouched, finish's shine only
            var okS = false; try { okS = a.apply(idxs[0], key, 'shine') !== false; } catch (e) { okS = false; }
            res.applied = okS ? idxs.length : 0; res.failed = okS ? 0 : 1; return res;
        }
        idxs.forEach(function (idx) {
            var st = null; try { st = a.partState(idx); } catch (e0) {}
            // ---- colour
            var cm = color ? color.mode : null, applyColor = null;
            if (cm === 'palette' || cm === 'custom' || cm === 'part') { if (isHex(color.hex)) { try { a.recolor(idx, color.hex); } catch (e1) {} } }
            else if (cm === 'keep') {
                if (!color.implied) { try { a.recolor(idx, null); } catch (e2) {} }                               // "keep its own colour" = the paint's own
                else if (st && st.colorMode !== 'pick') { try { a.recolor(idx, null); } catch (e3) {} }            // implied: only a colour the buyer chose survives
            }
            else if (cm === 'finish') { try { a.recolor(idx, null); } catch (e4) {} applyColor = 'finish'; }
            // 'asis': leave the colour exactly as it is
            // ---- finish
            if (key) {
                var ok = false; try { ok = a.apply(idx, key, 'part', applyColor ? { color: applyColor } : null) !== false; } catch (e5) { ok = false; }
                if (ok) res.applied++; else res.failed++;
            } else res.applied++;
            // ---- how much
            if (cmd.how === 'blend' && cmd.amount != null) { try { a.blend(idx, cmd.amount); } catch (e6) {} }
            else if (cmd.how === 'all' && st && st.blend < 1) { try { a.blend(idx, 1); } catch (e7) {} }
            // ---- fine adjustments
            var st2 = null; try { st2 = a.partState(idx); } catch (e8) {}
            var ao = st2 ? adjustOpts(cmd, st2) : null; if (ao) { try { a.adjust(idx, ao); } catch (e9) {} }
        });
        return res;
    }
    function execAdjust(cmd) {
        var a = A(), idxs = targetIdxs(cmd, true), res = { cmd: cmd, idxs: idxs, applied: 0, failed: 0 };
        if (!idxs.length) { res.failed = 1; res.msg = 'Nothing to change there.'; return res; }
        idxs.forEach(function (idx) {
            var st = null; try { st = a.partState(idx); } catch (e) {}
            var o = st ? adjustOpts(cmd, st) : null;
            if (o) { var ok = false; try { ok = a.adjust(idx, o) !== false; } catch (e2) {} if (ok) res.applied++; else res.failed++; } else res.failed++;
        });
        return res;
    }
    function shortLabel(plan) {
        var c = plan.cmds[0]; if (!c) return 'Easy: Tell Shokker';
        var d = NLU.describe(c, world());
        return 'Easy: ' + (plan.cmds.length > 1 ? plan.cmds.length + ' changes' : d.sentence).slice(0, 40);
    }
    function lineFor(res, w) {
        var c = res.cmd, d = NLU.describe(c, w);
        var line = { text: d.sentence, ok: res.failed === 0 && res.applied > 0, key: c.finish ? c.finish.key : null, hex: (c.color && (c.color.mode === 'palette' || c.color.mode === 'custom' || c.color.mode === 'part')) ? c.color.hex : null, count: res.idxs.length };
        if (res.failed && !res.applied) line.text = res.msg || ('Could not apply ' + (c.finish ? c.finish.name : 'that') + '.');
        return line;
    }
    function runPlan(plan, meta) {
        var a = A(), w = world(), rec = { id: ++S.uid, text: plan.text, lines: [], notes: (plan.notes || []).slice(), fixes: plan.fixes || [], cmds: plan.cmds, when: Date.now(), cands: null, ci: 0, undone: false, surprise: false, recipe: null, top: null, undoable: false, label: '' };
        var before = null; try { before = a.historyTop(); } catch (e) {}
        var firstIdx = -1, tgtRefs = [], results = [];
        try {
            a.batch(shortLabel(plan), function () {
                plan.cmds.forEach(function (c) {
                    var res = null;
                    try {
                        if (c.type === 'style') res = execStyle(c, rec);
                        else if (c.type === 'adjust') res = execAdjust(c);
                        else if (c.type === 'look') { a.look(c.id); res = { cmd: c, idxs: [], applied: 1, failed: 0 }; }
                    } catch (err) { try { console.warn('[EASY TELL]', err); } catch (e2) {} res = { cmd: c, idxs: [], applied: 0, failed: 1, msg: 'That one did not work — ' + (err && err.message ? err.message : 'unknown error') }; }
                    if (res) { results.push(res); if (firstIdx < 0 && res.idxs.length) firstIdx = res.idxs[0]; }
                });
            });
        } catch (err2) { try { console.warn('[EASY TELL]', err2); } catch (e3) {} }
        results.forEach(function (r) {
            rec.lines.push(lineFor(r, w));
            (r.cmd.targets || []).forEach(function (t) { if (t.kind !== 'whole' || true) tgtRefs.push(t); });
            if (r.cmd.recipe) { rec.recipe = r.cmd.recipe; S.lastRecipe = r.cmd.recipe; }
            if (r.cmd.surprise) rec.surprise = true;
        });
        // one lead line for a whole recipe instead of one per part
        var recipeCmds = plan.cmds.filter(function (c) { return c.recipe && c.role; });
        if (recipeCmds.length > 1) {
            var rc0 = NLU.recipeById(recipeCmds[0].recipe);
            rec.lines = [{ text: (rec.surprise ? 'Surprise: ' : '') + '“' + (rc0 ? rc0.label : 'Look') + '” on ' + recipeCmds.length + ' parts' + (rc0 ? ' — ' + rc0.blurb : ''), ok: true, key: null, hex: null, count: 0 }];
        } else if (plan.cmds.length === 1 && plan.cmds[0].type === 'look') {
            rec.lines = [{ text: '“' + plan.cmds[0].label + '” look — ' + (plan.cmds[0].blurb || ''), ok: true, key: null, hex: null, count: 0 }];
        }
        var primary = null; for (var i = 0; i < plan.cmds.length; i++) if (plan.cmds[i].type === 'style' && plan.cmds[i].finish && plan.cmds[i].finish.alts && plan.cmds[i].finish.alts.length) { primary = i; break; }
        if (primary != null) { var f = plan.cmds[primary].finish; rec.cands = [f.key].concat(f.alts); rec.primary = primary; }
        if (rec.recipe) rec.canReroll = true;
        try { rec.top = a.historyTop(); } catch (e4) {}
        rec.undoable = rec.top !== before;
        if (meta && meta.ai) { rec.ai = meta.ai; rec.cands = null; rec.canReroll = false; }
        if (tgtRefs.length) S.last = { targets: dedupeTargets(tgtRefs) };
        S.feed.unshift(rec); if (S.feed.length > 6) S.feed.length = 6;
        S.phrase = ''; S.plan = null; S.pending = null; S.help = false; S.confirmStart = false;
        if (_input) _input.value = '';
        flashTargets(firstIdx, plan);
        render();
        return rec;
    }
    function dedupeTargets(list) { var seen = {}, out = []; list.forEach(function (t) { var k = t.kind + ':' + (t.idx != null ? t.idx : (t.layerId != null ? t.layerId : '')); if (!seen[k]) { seen[k] = 1; out.push(t); } }); return out; }
    function flashTargets(idx, plan) {
        var a = A(); if (!a) return;
        try {
            var whole = plan.cmds.some(function (c) { return c.type === 'look' || (c.targets || []).some(function (t) { return t.kind === 'whole' || t.kind === 'colors'; }); });
            if (whole) { a.hover(-1); return; }
            if (idx != null && idx >= 0) { a.hover(idx); if (_flashTimer) clearTimeout(_flashTimer); _flashTimer = setTimeout(function () { try { a.unhover(); } catch (e) {} }, 1300); }
        } catch (e2) {}
    }

    // ------------------------------------------------------------ non-style commands
    function doUndo() {
        var a = A(); var ok = false; try { ok = a.undo() !== false; } catch (e) {}
        if (!ok) toast('Nothing to undo yet.');
        if (ok && S.feed[0] && !S.feed[0].undone) S.feed[0].undone = true;
        return ok;
    }
    function doRedo() { var a = A(); var ok = false; try { ok = a.redo() !== false; } catch (e) {} if (!ok) toast('Nothing to redo.'); return ok; }
    // the stock "Undone: …" toast is noise when undo is just the first half of ◀ ▶ (undo + redo with the next match)
    function quiet(fn) { var orig = window.showToast; window.showToast = function () {}; try { return fn(); } finally { window.showToast = orig; } }
    function canUndoRec(rec) { var a = A(); try { return !!(rec && !rec.undone && rec.undoable && a.historyTop() === rec.top); } catch (e) { return false; } }
    function undoRec(rec) {
        if (!canUndoRec(rec)) { toast('Something newer changed — use UNDO in the toolbar to step back further.'); render(); return; }
        var ok = false; try { ok = A().undo() !== false; } catch (e) {}
        if (ok) { rec.undone = true; }
        render();
    }
    function rerun(rec, delta) {
        // ◀ ▶ on a receipt: undo this step (when it is still the latest), then redo it with the next finish / the next look
        var a = A(); if (!a) return;
        var still = canUndoRec(rec);
        var w = world();
        if (rec.canReroll && rec.recipe) {
            var ids = NLU.RECIPES.map(function (r) { return r.id; }), at = ids.indexOf(rec.recipe), nx = ids[(at + (delta || 1) + ids.length) % ids.length];
            if (still) { try { quiet(function () { a.undo(); }); } catch (e) {} }
            var phrase = NLU.recipeById(nx).words[0], p2 = NLU.parse(phrase, w, {});
            var r2 = runPlan(p2, { reroll: true }); if (r2) { r2.text = rec.text; r2.rerollOf = rec.id; }
            return;
        }
        if (!rec.cands || rec.cands.length < 2) { toast('That was the only match — try describing it differently.'); return; }
        rec.ci = (rec.ci + (delta || 1) + rec.cands.length) % rec.cands.length;
        var key = rec.cands[rec.ci], nf = finInfo(key);
        var cmds = rec.cmds.map(function (c) { var n = {}; for (var k in c) if (c.hasOwnProperty(k)) n[k] = c[k]; return n; });
        var pc = cmds[rec.primary];
        pc.finish = { key: key, name: nf ? nf.name : key, via: pc.finish.via, family: pc.finish.family, alts: pc.finish.alts };
        if (still) { try { quiet(function () { a.undo(); }); } catch (e2) {} }
        var keepCands = rec.cands.slice(), keepCi = rec.ci, keepText = rec.text, keepFixes = rec.fixes;
        var nr = runPlan({ text: rec.text, cmds: cmds, notes: [], fixes: [] }, { reroll: true });
        if (nr) { nr.cands = keepCands; nr.ci = keepCi; nr.primary = rec.primary; nr.fixes = keepFixes; nr.text = keepText; S.feed.splice(S.feed.indexOf(rec), 1); render(); }
    }
    function doAnother(cmd) {
        var rec = S.feed[0];
        if (!rec) { toast('Nothing to change yet — tell me something first.'); return; }
        rerun(rec, 1);
    }

    // ------------------------------------------------------------ entering / running the phrase
    function parseNow(text) { return NLU.parse(text, world(), {}); }
    function submit(text, force) {
        text = String(text == null ? '' : text).trim(); if (!text) return;
        if (S.hist[0] !== text) S.hist.unshift(text); if (S.hist.length > 30) S.hist.length = 30; S.histAt = -1;
        var plan = (S.plan && S.planFor === text) ? S.plan : parseNow(text);
        var ai = window.spbEasyAI, go = 'local';
        try { if (ai) go = ai.route(plan, text, !!force || !!S.aiAsk); } catch (e) { go = 'local'; }
        if (go === 'ai') { runAI(text, plan); return; }
        execute(plan);
    }
    // ---- the optional AI copilot (js/spb-easy-ai.js): same executor, same receipts, one undo point
    function runAI(text, plan) {
        var ai = window.spbEasyAI; if (!ai) { execute(plan); return; }
        if (ai.busy()) { toast('Still working on the last one…'); return; }
        S.aiAsk = null; S.aiError = null; S.selectPrompt = null; S.help = false; S.aiPanel = false;
        S.ai = { text: text, tools: 0, t0: Date.now() };
        S.phrase = ''; S.plan = null; S.pending = null; if (_input) _input.value = '';
        render();
        ai.ask(text, { onEvent: function (type, d) { if (S.ai && type === 'tool') { S.ai.tools++; S.ai.last = d && d.name; render(); } } }).then(function (r) { finishAI(r, text, plan, ''); });
    }
    function finishAI(r, text, plan, tag) {
        S.ai = null;
        var meta = { ai: { text: r.text || '', usage: r.usage, model: r.model, calls: r.calls, refine: tag === 'refine' } };
        if (r.error) { if (r.error.error === 'aborted') { render(); return; } S.aiError = { message: r.error.message || 'The AI did not answer.', code: r.error.error, text: text, plan: plan }; render(); return; }
        if (r.asked) S.aiAsk = { question: r.asked.question, options: r.asked.options || [] };
        var label = tag === 'refine' ? '“look & refine” — ' + text : text;
        if (r.queue && r.queue.length) { runPlan({ text: label, cmds: r.queue, notes: [], fixes: [] }, meta); return; }
        var rec = { id: ++S.uid, text: label, lines: [], notes: [], fixes: [], cmds: [], when: Date.now(), undone: false, undoable: false, ai: meta.ai, chatOnly: true };
        if (!r.text && !r.asked) rec.ai.text = r.capped ? 'I got stuck on that one — try saying it a bit differently.' : (tag === 'refine' ? 'I looked at it and would leave it as it is.' : 'I did not find anything to change for that.');
        S.feed.unshift(rec); if (S.feed.length > 6) S.feed.length = 6;
        render();
    }
    function plainText(t) { return String(t).replace(/^“look & refine” — /, ''); }
    // "look & refine": wait for the live render to settle, hand the AI a picture of it, let it improve the design (opt-in, one button)
    function runRefine(rec) {
        var ai = window.spbEasyAI, a = A(); if (!ai || !a) return;
        if (ai.busy()) { toast('Still working on the last one…'); return; }
        S.aiAsk = null; S.aiError = null; S.aiPanel = false;
        S.ai = { text: rec.text, tools: 0, t0: Date.now(), waiting: true }; render();
        a.whenSettled(30000).then(function () {
            if (!S.ai) return;
            var img = a.liveSnapshot(512);
            if (!img) { S.ai = null; S.aiError = { message: 'There is no preview picture to look at yet.', code: 'noimg' }; render(); return; }
            S.ai.waiting = false; render();
            ai.refine(plainText(rec.text), img, { onEvent: function (type) { if (S.ai && type === 'tool') { S.ai.tools++; render(); } } }).then(function (r) { finishAI(r, plainText(rec.text), null, 'refine'); });
        });
    }
    function execute(plan) {
        var i, c;
        for (i = 0; i < plan.cmds.length; i++) {
            c = plan.cmds[i];
            if (c.type === 'undo') { doUndo(); clearInput(); render(); return; }
            if (c.type === 'redo') { doRedo(); clearInput(); render(); return; }
            if (c.type === 'startover') { S.confirmStart = true; clearInput(); render(); return; }
            if (c.type === 'help') { S.help = true; clearInput(); render(); return; }
            if (c.type === 'save') { clearInput(); saveHint(); render(); return; }
            if (c.type === 'another') { doAnother(c); clearInput(); render(); return; }
        }
        var acting = plan.cmds.filter(function (x) { return x.type === 'style' || x.type === 'adjust' || x.type === 'look'; });
        var selects = plan.cmds.filter(function (x) { return x.type === 'select'; });
        if (!acting.length && selects.length && !plan.cmds.some(function (x) { return x.needsTarget; })) { showSelect(selects[0]); clearInput(); return; }
        if (!plan.cmds.length) { S.plan = plan; S.planFor = S.phrase; render(); pulse(); return; }
        if (plan.cmds.some(function (x) { return x.needsTarget && (x.type === 'style' || x.type === 'adjust'); })) { S.pending = plan; S.plan = plan; S.planFor = plan.text; render(); return; }
        runPlan(plan);
    }
    // "save" / "I'm done": SPB never saves for you (it writes into iRacing) — it points at the button
    function saveHint() {
        var b = $('spbEasySave');
        if (b) { try { b.scrollIntoView({ block: 'nearest' }); } catch (e) {} b.classList.remove('spb-tell-pulse'); void b.offsetWidth; b.classList.add('spb-tell-pulse'); setTimeout(function () { b.classList.remove('spb-tell-pulse'); }, 2600); }
        toast('Nothing is saved until YOU press SAVE TO iRACING — it’s glowing now.');
    }
    function clearInput() { S.phrase = ''; S.plan = null; S.pending = null; if (_input) _input.value = ''; }
    function showSelect(cmd) {
        var a = A(), idxs = targetIdxs(cmd, false);
        if (idxs.length) { try { a.hover(idxs[0]); if (_flashTimer) clearTimeout(_flashTimer); _flashTimer = setTimeout(function () { try { a.unhover(); } catch (e) {} }, 1600); } catch (e) {} }
        else if (cmd.targets[0] && cmd.targets[0].kind === 'layer') { try { a.hoverLayer(cmd.targets[0].layerId); if (_flashTimer) clearTimeout(_flashTimer); _flashTimer = setTimeout(function () { try { a.unhover(); } catch (e2) {} }, 1600); } catch (e3) {} }
        S.selectPrompt = { who: NLU.whoText(cmd, world()), cmd: cmd };
        render();
    }
    function chooseTarget(t) {
        var plan = S.pending; if (!plan) return;
        var done = false;
        plan.cmds.forEach(function (c) { if (!done && c.needsTarget) { c.targets = [t]; c.needsTarget = false; c.options = null; c.question = null; done = true; } });   // one answer settles ONE question
        if (plan.cmds.some(function (c) { return c.needsTarget && (c.type === 'style' || c.type === 'adjust'); })) { S.pending = plan; S.plan = plan; S.planFor = plan.text; render(); return; }
        S.pending = null; runPlan(plan);
    }
    // while you type, the first thing the sentence points at lights up on the car
    function previewTarget(plan) {
        var a = A(); if (!a) return;
        try {
            var c = plan && plan.cmds ? plan.cmds.filter(function (x) { return x.targets && x.targets.length && !x.needsTarget; })[0] : null, t = c ? c.targets[0] : null;
            if (!t || t.kind === 'whole' || t.kind === 'colors') { a.unhover(); return; }
            if (t.kind === 'part') a.hover(t.idx);
            else if (t.kind === 'layer') { var li = idxOfLayer(t.layerId, false); if (li >= 0) a.hover(li); else a.hoverLayer(t.layerId); }
        } catch (e) {}
    }
    function acceptComp(i) {
        var c = S.comps && S.comps[i]; if (!c || !_input) return;
        var v = _input.value, low = v.toLowerCase(), at = low.lastIndexOf(c.replace);
        if (at < 0) at = v.length;
        _input.value = v.slice(0, at) + c.text + ' '; S.phrase = _input.value; S.comps = [];
        try { S.plan = parseNow(S.phrase); S.planFor = S.phrase; } catch (e) { S.plan = null; }
        render(); previewTarget(S.plan); _input.focus(); try { var n = _input.value.length; _input.setSelectionRange(n, n); } catch (e2) {}
    }
    function pulse() { if (!_dock) return; _dock.classList.remove('shake'); void _dock.offsetWidth; _dock.classList.add('shake'); }

    // ------------------------------------------------------------ rendering
    function chipHtmlPart(t, w) {
        var label = NLU.whoText({ targets: [t], exclude: [] }, w);
        var attr = t.kind === 'layer' ? 'data-hlayer="' + esc(t.layerId) + '"' : (t.kind === 'part' ? 'data-hpart="' + t.idx + '"' : '');
        var ps = w.parts || [], hex = null; if (t.kind === 'part') for (var i = 0; i < ps.length; i++) if (ps[i].idx === t.idx) hex = ps[i].hex;
        var icon = t.kind === 'layer' ? '<i class="spb-tell-ic layer" title="PSD layer"></i>' : (t.kind === 'whole' ? '<i class="spb-tell-ic whole"></i>' : '<i class="spb-tell-sw" style="background:' + esc(hex || '#666') + '"></i>');
        return '<span class="spb-tell-chip tgt" ' + attr + '>' + icon + esc(label) + '</span>';
    }
    function swatchChip(cmd) {
        var c = cmd.color; if (!c) return '';
        if (c.implied && c.mode !== 'finish' && c.mode !== 'asis') return '';
        if (c.implied) return '';
        if (c.mode === 'keep') return '<span class="spb-tell-chip col">keep its colour</span>';
        if (c.mode === 'finish') return '<span class="spb-tell-chip col">the finish’s own colour</span>';
        if (c.mode === 'asis') return '';
        return '<span class="spb-tell-chip col"><i class="spb-tell-sw" style="background:' + esc(c.hex) + '"></i>' + esc(c.mode === 'part' ? ('the ' + (c.word || 'colour') + ' from ' + (c.from || 'the car')) : (c.name && c.name !== c.hex ? c.name : (c.word || c.hex))) + '</span>';
    }
    function finishChip(cmd) {
        var f = cmd.finish; if (!f) return '';
        var t = thumb(f.key), fi = finInfo(f.key);
        var img = t ? '<img class="spb-tell-thumb" alt="" src="' + esc(t) + '" onerror="this.style.display=\'none\'">' : (fi && isHex(fi.swatch) ? '<i class="spb-tell-sw" style="background:' + esc(fi.swatch) + '"></i>' : '');
        return '<span class="spb-tell-chip fin" title="' + esc(fi && fi.desc ? fi.desc : f.name) + '">' + img + esc(f.name) + '</span>';
    }
    function cmdCardHtml(cmd, w, idx) {
        var h = '<div class="spb-tell-card' + (cmd.needsTarget ? ' need' : '') + '">';
        if (cmd.type === 'style') {
            h += (cmd.needsTarget ? '<span class="spb-tell-chip tgt need">which part?</span>' : (cmd.targets || []).map(function (t) { return chipHtmlPart(t, w); }).join(''));
            if (cmd.exclude && cmd.exclude.length) h += '<span class="spb-tell-mut">except</span>' + cmd.exclude.map(function (t) { return chipHtmlPart(t, w); }).join('');
            h += '<span class="spb-tell-arrow">→</span>';
            var bits = finishChip(cmd) + swatchChip(cmd);
            if (cmd.how === 'shine') bits += '<span class="spb-tell-chip how">just the shine</span>';
            else if (cmd.how === 'blend') bits += '<span class="spb-tell-chip how">' + Math.round((cmd.amount == null ? 0.5 : cmd.amount) * 100) + '% blend</span>';
            if (cmd.adjusts && cmd.adjusts.length) bits += cmd.adjusts.map(function (a) { return '<span class="spb-tell-chip how">' + esc(NLU.adjustWords(a)) + '</span>'; }).join('');
            h += bits || '<span class="spb-tell-mut">(no change)</span>';
        } else if (cmd.type === 'adjust') {
            h += (cmd.needsTarget ? '<span class="spb-tell-chip tgt need">which part?</span>' : (cmd.targets || []).map(function (t) { return chipHtmlPart(t, w); }).join('')) + '<span class="spb-tell-arrow">→</span>' + cmd.adjusts.map(function (a) { return '<span class="spb-tell-chip how">' + esc(NLU.adjustWords(a)) + '</span>'; }).join('');
        } else if (cmd.type === 'look') {
            h += '<span class="spb-tell-chip tgt"><i class="spb-tell-ic whole"></i>the whole car</span><span class="spb-tell-arrow">→</span><span class="spb-tell-chip fin">“' + esc(cmd.label) + '” look</span>';
        } else if (cmd.type === 'select') {
            h += (cmd.targets[0] ? chipHtmlPart(cmd.targets[0], w) : '<span class="spb-tell-chip tgt need">which part?</span>') + '<span class="spb-tell-mut">show me this part</span>';
        } else h += '<span class="spb-tell-chip">' + esc(cmd.type) + '</span>';
        h += '</div>';
        return h;
    }
    // "Which part?" choices: the car's biggest parts (dark and white ones too), then its layers, then the whole car
    function defaultOptions(w) {
        var opts = [], ps = (w.parts || []).filter(function (p) { return p.kind !== 'layer' && !p.pick; }).sort(function (a, b) { return (b.share || 0) - (a.share || 0); }).slice(0, 6);
        ps.forEach(function (p) { opts.push({ kind: 'part', idx: p.idx, label: p.label || p.name }); });
        (w.layers || []).slice(0, 6).forEach(function (l) { opts.push({ kind: 'layer', layerId: l.id, name: l.name }); });
        opts.push({ kind: 'whole' });
        return opts;
    }
    function optionsHtml(cmd, w) {
        var opts = cmd.options;
        if (!opts || !opts.length) opts = defaultOptions(w);
        var finder = '';                                            // a flat paint has no numbers layer: the finder can cut them out (opt-in, ~40 s)
        if (cmd.unknownNoun && /number|sponsor|logo|text|letter|name/i.test(cmd.unknownNoun) && !(w.layers || []).length) finder = '<button type="button" class="spb-tell-opt hot" data-act="findnum" title="Look for the numbers and sponsor text on your paint, so they can take their own finish (about 40 seconds)">🔎 Find my numbers &amp; sponsors <small>(~40 s)</small></button>';
        return '<div class="spb-tell-ask"><b>' + esc(cmd.question || 'Which part?') + '</b><div class="spb-tell-askrow">' + finder + opts.map(function (t, i) { return '<button type="button" class="spb-tell-opt" data-opt="' + i + '">' + chipHtmlPart(t, w) + '</button>'; }).join('') + '</div></div>';
    }
    function planHtml(plan, w) {
        var h = '';
        if (!plan.cmds.length) {
            h += '<div class="spb-tell-none"><b>I didn’t catch that.</b> Try naming a part and what you want: <i>make the numbers gold chrome</i>.' + (plan.leftover.length ? ' <span class="spb-tell-mut">(couldn’t use: ' + esc(plan.leftover.join(', ')) + ')</span>' : '') + '</div>';
            var alt = ideasHtml(w, 3); S._ideas = alt.ideas; h += alt.html.replace('<span class="spb-tell-lab">Try</span>', '<span class="spb-tell-lab">Maybe</span>');
            var aiSt = null; try { aiSt = window.SpbAI && window.SpbAI.cached(); } catch (eA) {}
            if (!(aiSt && aiSt.configured)) h += '<div class="spb-tell-note">Want to just talk to it in your own words? <button type="button" class="spb-tell-tw" data-act="aisettings">✦ Turn on the optional AI copilot</button></div>';
        } else {
            var shown = plan.cmds.length > 5 ? plan.cmds.slice(0, 5) : plan.cmds;
            h += '<div class="spb-tell-understood"><span class="spb-tell-lab">I’ll do</span>' + shown.map(function (c, i) { return cmdCardHtml(c, w, i); }).join('') + (plan.cmds.length > 5 ? '<span class="spb-tell-mut">+' + (plan.cmds.length - 5) + ' more</span>' : '') + '</div>';
            var asks = plan.cmds.filter(function (c) { return c.needsTarget; });
            if (asks.length) h += optionsHtml(asks[0], w);
        }
        if (plan.fixes && plan.fixes.length) h += '<div class="spb-tell-note">read <i>' + esc(plan.fixes.map(function (f) { return f[0] + ' → ' + f[1]; }).join(', ')) + '</i></div>';
        (plan.notes || []).forEach(function (n) { h += '<div class="spb-tell-note warn">' + esc(n) + '</div>'; });
        if (plan.cmds.length && plan.leftover && plan.leftover.length) h += '<div class="spb-tell-note">didn’t use: <i>' + esc(plan.leftover.join(', ')) + '</i></div>';
        return h;
    }
    function compactReceiptHtml(rec) {
        var undoOk = canUndoRec(rec), first = rec.lines[0] ? rec.lines[0].text : '';
        return '<div class="spb-tell-rec mini' + (rec.undone ? ' undone' : '') + '" data-rec="' + rec.id + '"><span class="spb-tell-said">' + (rec.ai && rec.ai.refine ? esc(rec.text) : '“' + esc(rec.text) + '”') + '</span><span class="spb-tell-sum">→ ' + esc(first) + (rec.lines.length > 1 ? ' <small>+' + (rec.lines.length - 1) + '</small>' : '') + '</span>' +
            (rec.undone ? '<span class="spb-tell-undone">undone</span>' : '<button type="button" class="spb-tell-mini' + (undoOk ? '' : ' off') + '" data-act="undo" title="' + (undoOk ? 'Undo just this' : 'Something newer changed — use UNDO in the toolbar') + '">↶</button>') + '</div>';
    }
    function receiptHtml(rec, isTop) {
        var undoOk = canUndoRec(rec), h = '<div class="spb-tell-rec' + (rec.undone ? ' undone' : '') + (isTop ? ' top' : '') + '" data-rec="' + rec.id + '">';
        if (rec.ai && rec.ai.text) { /* placed after the head, below */ }
        h += '<div class="spb-tell-rec-head"><span class="spb-tell-said">' + (rec.ai && rec.ai.refine ? esc(rec.text) : '“' + esc(rec.text) + '”') + '</span>';
        h += '<span class="spb-tell-rec-actions">';
        if (rec.undone) h += '<span class="spb-tell-undone">undone</span>';
        else {
            if (rec.ai && rec.cmds && rec.cmds.length && !rec.ai.refine) h += '<button type="button" class="spb-tell-mini" data-act="airefine" title="The AI looks at the rendered result and improves it (a little extra cost)">\uD83D\uDC41 look &amp; refine</button>';
            if (rec.ai && rec.cmds && rec.cmds.length) h += '<button type="button" class="spb-tell-mini try" data-act="aitake" title="Undo this and ask the AI for a noticeably different take">✦ another take</button>';
            if ((rec.cands && rec.cands.length > 1) || rec.canReroll) h += '<button type="button" class="spb-tell-mini" data-act="prev" title="Previous match">◀</button><button type="button" class="spb-tell-mini try" data-act="next" title="Try another match for the same words">try another ▶</button>';
            h += '<button type="button" class="spb-tell-mini' + (undoOk ? '' : ' off') + '" data-act="undo" title="' + (undoOk ? 'Undo just this' : 'Something newer changed — use UNDO in the toolbar') + '">↶ undo</button>';
        }
        h += '</span></div>';
        if (rec.ai && rec.ai.text) h += '<div class="spb-tell-aitext">✦ ' + esc(rec.ai.text) + '</div>';
        rec.lines.forEach(function (l) {
            var img = l.key ? thumb(l.key) : '';
            h += '<div class="spb-tell-line' + (l.ok ? '' : ' bad') + '">' + (img ? '<img class="spb-tell-thumb" alt="" src="' + esc(img) + '" onerror="this.style.display=\'none\'">' : (l.hex ? '<i class="spb-tell-sw" style="background:' + esc(l.hex) + '"></i>' : '<i class="spb-tell-ck">' + (l.ok ? '✓' : '!') + '</i>')) + '<span>' + esc(l.text) + '</span></div>';
        });
        if (rec.ai) h += '<div class="spb-tell-alt">' + aiCostText(rec.ai) + '</div>';
        if (rec.cands && rec.cands.length > 1 && !rec.undone) h += '<div class="spb-tell-alt">match ' + (rec.ci + 1) + ' of ' + rec.cands.length + '</div>';
        (rec.notes || []).forEach(function (n) { h += '<div class="spb-tell-note warn">' + esc(n) + '</div>'; });
        if (isTop && !rec.undone && rec.lines.length && rec.cmds.some(function (c) { return (c.type === 'style' || c.type === 'adjust') && !c.recipe; })) {
            h += '<div class="spb-tell-tweaks"><span class="spb-tell-lab">Tweak</span>' + TWEAKS.map(function (t) { return '<button type="button" class="spb-tell-tw" data-tweak="' + esc(t[1]) + '" title="' + esc('Say: “' + t[1] + '”') + '">' + esc(t[0]) + '</button>'; }).join('') + '</div>';
        }
        h += '</div>';
        return h;
    }
    var TWEAKS = [['darker', 'darker'], ['brighter', 'brighter'], ['more vivid', 'more vivid'], ['calmer', 'muted'], ['bigger', 'bigger'], ['finer', 'finer'], ['less', 'a bit less']];
    function ideasHtml(w, max) {
        var ideas = []; try { ideas = NLU.suggest(w, { seed: S.seed }); } catch (e) {}
        var h = '<div class="spb-tell-ideas"><span class="spb-tell-lab">Try</span>';
        ideas.slice(0, max || 9).forEach(function (s, i) { h += '<button type="button" class="spb-tell-idea ' + s.kind + '" data-idea="' + i + '" title="' + esc('Say: “' + s.phrase + '”') + '">' + (s.hex ? '<i class="spb-tell-sw" style="background:' + esc(s.hex) + '"></i>' : '') + esc(s.label) + '</button>'; });
        h += '</div>';
        return { html: h, ideas: ideas };
    }
    var HELP = [
        ['Change a part', ['make the cyan candy', 'the yellow gold chrome', 'turn the black white']],
        ['Use your layers', ['numbers white chrome', 'make the sponsors matte black', 'the tape pearl white']],
        ['Whole car', ['everything matte except the sponsors', 'the whole car candy red', 'carbon fiber everything']],
        ['Several at once', ['numbers gold, sponsors silver, body candy blue']],
        ['A vibe', ['make it look expensive', 'stealth', 'race day', 'retro', 'surprise me']],
        ['Fine-tune', ['darker', 'bigger flakes', 'more vivid', 'a little less', 'just the shine']],
        ['Fix it', ['undo', 'try another', 'start over']]
    ];
    function helpHtml() {
        var h = '<div class="spb-tell-help"><b>Say it however you like — I know your car’s colours and layers.</b>';
        HELP.forEach(function (g) { h += '<div class="spb-tell-helprow"><span class="spb-tell-lab">' + g[0] + '</span>' + g[1].map(function (p) { return '<button type="button" class="spb-tell-idea ph" data-phrase="' + esc(p) + '">' + esc(p) + '</button>'; }).join('') + '</div>'; });
        h += '<div class="spb-tell-mut">Tip: press <kbd>/</kbd> anywhere to jump here. I understand typos, colour names like “burgundy”, and finish words like “sparkly”, “rusty” or “wet look”.</div></div>';
        return h;
    }
    function aiCostText(ai) { if (!ai || !ai.usage) return ''; var c = Number(ai.usage.cost || 0); return '✦ ' + (c ? '$' + (c < 0.01 ? c.toFixed(4) : c.toFixed(3)) : 'free') + ' · ' + esc(String(ai.model || '').replace(/^.*\//, '')) + ' · ' + (ai.calls || 1) + ' call' + ((ai.calls || 1) > 1 ? 's' : ''); }
    function bodyHtml() {
        var w = world(), h = '';
        if (S.ai) {
            var secs = Math.max(0, Math.round((Date.now() - S.ai.t0) / 1000));
            h += '<div class="spb-tell-aibusy"><span class="spb-tell-dots"><i></i><i></i><i></i></span><span><b>' + (S.ai.waiting ? 'Waiting for the preview…' : 'Thinking…') + '</b> <small>' + esc(S.ai.waiting ? 'so the AI can look at the finished render' : (S.ai.tools ? ('working on it · ' + S.ai.tools + ' step' + (S.ai.tools > 1 ? 's' : '')) : 'reading your car and your words')) + '</small></span><button type="button" class="spb-tell-mini" data-act="aicancel">Cancel</button></div>';
        }
        if (S.aiError) {
            var e0 = S.aiError, noKey = e0.code === 'no_key' || e0.code === 'bad_key';
            h += '<div class="spb-tell-ask bad"><b>' + esc(e0.message) + '</b><div class="spb-tell-askrow">' + (noKey || e0.code === 'no_credit' ? '<button type="button" class="spb-tell-opt hot" data-act="aisettings">Open AI settings</button>' : '') + (e0.plan && e0.plan.cmds && e0.plan.cmds.length ? '<button type="button" class="spb-tell-opt" data-act="aifallback">Use the built-in parser instead</button>' : '') + '<button type="button" class="spb-tell-opt" data-act="aidismiss">Dismiss</button></div></div>';
        }
        if (S.aiAsk) {
            h += '<div class="spb-tell-ask ai"><b>✦ ' + esc(S.aiAsk.question) + '</b>' + (S.aiAsk.options.length ? '<div class="spb-tell-askrow">' + S.aiAsk.options.map(function (o, i) { return '<button type="button" class="spb-tell-opt" data-aiopt="' + i + '"><span class="spb-tell-chip">' + esc(o) + '</span></button>'; }).join('') + '</div>' : '') + '<div class="spb-tell-mut">Tap one, or just type your answer.</div></div>';
        }
        if (S.aiPanel) h += '<div id="spbEasyTellAIHost"></div>';
        if (S.confirmStart) {
            h += '<div class="spb-tell-ask"><b>Start over? This rebuilds your parts from the paint and drops every finish you set.</b><div class="spb-tell-askrow"><button type="button" class="spb-tell-opt hot" data-act="startyes">Yes, start over</button><button type="button" class="spb-tell-opt" data-act="startno">Keep working</button></div><div class="spb-tell-mut">UNDO brings the old design back.</div></div>';
        }
        if (S.selectPrompt && !S.phrase) {
            var sp = S.selectPrompt, fams = ['candy', 'chrome', 'pearl', 'matte', 'carbon', 'flake'];
            h += '<div class="spb-tell-ask"><b>What should ' + esc(sp.who) + ' look like?</b><div class="spb-tell-askrow">' + fams.map(function (f) { return '<button type="button" class="spb-tell-idea ph" data-phrase="make ' + esc(NLU.norm(sp.who) === 'the whole car' ? 'everything' : 'the ' + sp.who.replace(/^the /i, '').toLowerCase()) + ' ' + f + '">' + f + '</button>'; }).join('') + '</div></div>';
        }
        if (S.phrase.trim() && S.comps && S.comps.length) {
            h += '<div class="spb-tell-comp"><span class="spb-tell-lab">Tab</span>' + S.comps.map(function (c, i) { return '<button type="button" class="spb-tell-cc ' + c.kind + '" data-comp="' + i + '" title="Complete to ' + esc(c.text) + '">' + esc(c.text) + '</button>'; }).join('') + '</div>';
        }
        if (S.phrase.trim()) {
            var plan = (S.plan && S.planFor === S.phrase) ? S.plan : null;
            if (plan) h += planHtml(plan, w);
        } else if (S.pending) h += planHtml(S.pending, w);
        if (S.help && !S.phrase.trim()) h += helpHtml();
        var idea = null, typing = !!S.phrase.trim();
        var showIdeas = !typing && !S.help && !S.confirmStart && (!S.feed.length || S.focus);
        if (showIdeas) { idea = ideasHtml(w, S.feed.length ? 4 : 9); h += idea.html; }
        if (S.feed.length) {
            var keep = typing ? 1 : (showIdeas && S.feed.length ? 1 : 2);
            h += '<div class="spb-tell-feed">' + S.feed.slice(0, keep).map(function (r, i) { return i === 0 ? receiptHtml(r, true) : compactReceiptHtml(r); }).join('') + '</div>';
        }
        S._ideas = idea ? idea.ideas : (S._ideas || []);
        return h;
    }

    function ensureDock() {
        var host = $('spbEasyProof'); if (!host) return null;
        if (_dock && _dock.parentNode === host) return _dock;
        _dock = $('spbEasyTell');
        if (_dock && _dock.parentNode !== host) { _dock.parentNode.removeChild(_dock); _dock = null; }
        if (!_dock) {
            _dock = document.createElement('div'); _dock.id = 'spbEasyTell'; _dock.className = 'spb-tell'; _dock.setAttribute('role', 'region'); _dock.setAttribute('aria-label', 'Tell Shokker what you want');
            _dock.innerHTML = '<div class="spb-tell-bar"><span class="spb-tell-badge" aria-hidden="true">✦</span>' +
                '<input id="spbEasyTellInput" class="spb-tell-input" type="text" autocomplete="off" spellcheck="false" aria-label="Tell Shokker what you want" placeholder="Tell Shokker what you want…">' +
                '<span class="spb-tell-status" title="Your live preview is being repainted"><i></i>painting…</span>' +
                '<button type="button" class="spb-tell-go" id="spbEasyTellGo" title="Do it (Enter)">Do it ⏎</button>' +
                '<button type="button" class="spb-tell-dice" id="spbEasyTellDice" title="Surprise me — a whole new look">🎲</button>' +
                '<button type="button" class="spb-tell-dice" id="spbEasyTellHelp" title="What can I say?">?</button>' +
                '<button type="button" class="spb-tell-aipill" id="spbEasyTellAI" title="AI copilot (optional)">✦ AI</button></div>' +
                '<div class="spb-tell-body" id="spbEasyTellBody" aria-live="polite"></div>';
            host.insertBefore(_dock, host.firstChild);
            _input = $('spbEasyTellInput'); wireDock();
        } else host.insertBefore(_dock, host.firstChild);
        _input = $('spbEasyTellInput');
        return _dock;
    }
    function render() {
        if (!ensureDock()) return;
        var show = ready();
        _dock.hidden = !show;
        if (!show) return;
        var body = $('spbEasyTellBody'); if (!body) return;
        var keepScroll = body.scrollTop;
        body.innerHTML = bodyHtml();
        body.scrollTop = keepScroll;
        _dock.classList.toggle('busy', !!S.phrase.trim());
        if (S.aiPanel && window.SpbAI) {
            var host = $('spbEasyTellAIHost');
            if (host) { if (!S.aiPanelEl) S.aiPanelEl = window.SpbAI.settingsPanel(function () { updatePill(); }); host.appendChild(S.aiPanelEl); }
        }
        updatePill();
    }
    function updatePill() {
        var b = $('spbEasyTellAI'); if (!b) return;
        var st = null; try { st = window.SpbAI && window.SpbAI.cached(); } catch (e) {}
        var on = !!(st && st.configured && st.mode !== 'off');
        b.classList.toggle('on', on); b.classList.toggle('open', !!S.aiPanel);
        b.title = on ? 'AI copilot is ON (' + (st.mode === 'always' ? 'every request' : 'when the parser is unsure') + ' · ' + st.model + '). Click for settings. Ctrl+Enter sends one request to the AI.' : 'AI copilot (optional): add your OpenRouter key so you can talk to Shokker in your own words.';
    }
    function rotatePlaceholder() {
        if (!_input || !ready()) return;
        if (S.phrase || document.activeElement === _input) return;
        var ideas = S._ideas && S._ideas.length ? S._ideas : NLU.suggest(world(), { seed: S.seed });
        var pool = ideas.filter(function (s) { return s.kind !== 'vibe'; }).concat(ideas.filter(function (s) { return s.kind === 'vibe'; }));
        var p = pool.length ? pool[S.tip++ % pool.length].phrase : 'make the numbers gold chrome';
        _input.placeholder = 'Tell Shokker what you want…  e.g. “' + p + '”';
    }

    // ------------------------------------------------------------ events
    function wireDock() {
        _input.addEventListener('input', function () {
            S.phrase = _input.value; S.selectPrompt = null; S.help = false;
            if (_timer) clearTimeout(_timer);
            _timer = setTimeout(function () {
                var t = S.phrase.trim();
                if (t) { try { S.plan = parseNow(S.phrase); S.planFor = S.phrase; } catch (e) { S.plan = null; try { console.warn('[EASY TELL] parse', e); } catch (e2) {} } } else { S.plan = null; }
                try { S.comps = t ? NLU.complete(S.phrase, world(), 6) : []; } catch (e3) { S.comps = []; }
                S.pending = null; render(); previewTarget(S.plan);
            }, 70);
        });
        _input.addEventListener('keydown', function (ev) {
            var k = ev.key;
            if (k === 'Enter' || ev.keyCode === 13) { ev.preventDefault(); if (_timer) { clearTimeout(_timer); _timer = null; } var t = _input.value; S.phrase = t; if (t.trim()) submit(t, !!(ev.ctrlKey || ev.metaKey)); return; }
            if ((k === 'Tab' || ev.keyCode === 9) && !ev.shiftKey && S.comps && S.comps.length && S.phrase.trim()) { ev.preventDefault(); acceptComp(0); return; }
            if (k === 'Escape' || ev.keyCode === 27) { ev.preventDefault(); ev.stopPropagation(); if (S.phrase || S.help || S.pending || S.confirmStart || S.selectPrompt) { clearInput(); S.help = false; S.confirmStart = false; S.selectPrompt = null; render(); } else _input.blur(); return; }
            if ((k === 'ArrowUp' || ev.keyCode === 38) && !S.phrase.trim() && S.hist.length) { ev.preventDefault(); S.histAt = Math.min(S.hist.length - 1, S.histAt + 1); _input.value = S.hist[S.histAt]; S.phrase = _input.value; S.plan = parseNow(S.phrase); S.planFor = S.phrase; render(); return; }
            ev.stopPropagation();                                            // typing must never reach Easy's own shortcuts (Ctrl+Z aside)
        });
        _input.addEventListener('focus', function () { S.focus = true; _dock.classList.add('focus'); if (!S.phrase.trim()) render(); });
        _input.addEventListener('blur', function () { setTimeout(function () { if (document.activeElement === _input) return; S.focus = false; _dock.classList.remove('focus'); if (!S.phrase.trim()) render(); }, 160); });   // delayed so a click on an idea chip lands first
        $('spbEasyTellGo').addEventListener('click', function () { var t = _input.value; S.phrase = t; if (t.trim()) submit(t); else { _input.focus(); pulse(); } });
        $('spbEasyTellDice').addEventListener('click', function () { submit('surprise me'); });
        $('spbEasyTellAI').addEventListener('click', function () { S.aiPanel = !S.aiPanel; S.help = false; S.selectPrompt = null; S.aiError = null; render(); });
        try { if (window.SpbAI) { window.SpbAI.onStatus(updatePill); window.SpbAI.status().then(updatePill); } } catch (e) {}
        $('spbEasyTellHelp').addEventListener('click', function () { S.help = !S.help; S.selectPrompt = null; clearInput(); render(); });
        _dock.addEventListener('click', onDockClick);
        _dock.addEventListener('mouseover', onDockHover);
        _dock.addEventListener('mouseout', function (ev) { var el = ev.target && ev.target.closest ? ev.target.closest('[data-hpart],[data-hlayer]') : null; if (el) { try { A().unhover(); } catch (e) {} } });
    }
    function closestAttr(el, names, stop) {
        while (el && el !== stop) { if (el.getAttribute) for (var i = 0; i < names.length; i++) if (el.hasAttribute(names[i])) return el; el = el.parentNode; }
        return null;
    }
    function onDockHover(ev) {
        var el = ev.target && ev.target.closest ? ev.target.closest('[data-hpart],[data-hlayer]') : null; if (!el) return;
        try { var a = A(); if (el.hasAttribute('data-hpart')) a.hover(Number(el.getAttribute('data-hpart'))); else a.hoverLayer(el.getAttribute('data-hlayer')); } catch (e) {}
    }
    function onDockClick(ev) {
        var el = closestAttr(ev.target, ['data-act', 'data-idea', 'data-phrase', 'data-opt', 'data-aiopt', 'data-comp', 'data-tweak', 'data-rec'], _dock); if (!el) return;
        var act = el.getAttribute('data-act');
        if (el.hasAttribute('data-idea')) { var s = (S._ideas || [])[Number(el.getAttribute('data-idea'))]; if (s) { if (_input) _input.value = s.phrase; S.phrase = s.phrase; submit(s.phrase); } return; }
        if (el.hasAttribute('data-comp')) { acceptComp(Number(el.getAttribute('data-comp'))); return; }
        if (el.hasAttribute('data-aiopt')) { var ao = S.aiAsk && S.aiAsk.options[Number(el.getAttribute('data-aiopt'))]; if (ao) { S.phrase = ao; submit(ao, true); } return; }
        if (act === 'airefine') {
            var rf = null; var re1 = closestAttr(el, ['data-rec'], _dock); if (re1) { var rid1 = Number(re1.getAttribute('data-rec')); S.feed.forEach(function (r) { if (r.id === rid1) rf = r; }); }
            if (rf) runRefine(rf); return;
        }
        if (act === 'aitake') {
            var rr = null; var re0 = closestAttr(el, ['data-rec'], _dock); if (re0) { var rid0 = Number(re0.getAttribute('data-rec')); S.feed.forEach(function (r) { if (r.id === rid0) rr = r; }); }
            if (rr) { var still0 = canUndoRec(rr); if (still0) { try { quiet(function () { A().undo(); }); } catch (e) {} rr.undone = true; } runAI(rr.text + ' — give me a noticeably different take than last time', parseNow(rr.text)); }
            return;
        }
        if (act === 'aicancel') { try { window.spbEasyAI.cancel(); } catch (e) {} S.ai = null; render(); return; }
        if (act === 'aisettings') { S.aiPanel = true; S.aiError = null; render(); return; }
        if (act === 'aidismiss') { S.aiError = null; render(); return; }
        if (act === 'aifallback') { var pl = S.aiError && S.aiError.plan; S.aiError = null; if (pl) execute(pl); else render(); return; }
        if (el.hasAttribute('data-tweak')) { var tw = el.getAttribute('data-tweak'); S.phrase = tw; submit(tw); return; }
        if (el.hasAttribute('data-phrase')) { var ph = el.getAttribute('data-phrase'); if (_input) _input.value = ph; S.phrase = ph; S.help = false; S.selectPrompt = null; submit(ph); return; }
        if (el.hasAttribute('data-opt')) {
            var plan = S.pending || S.plan; if (!plan) return;
            var ask = null; plan.cmds.forEach(function (c) { if (!ask && c.needsTarget) ask = c; });
            var w = world(), opts = ask && ask.options;
            if (!opts || !opts.length) opts = defaultOptions(w);
            var t = opts[Number(el.getAttribute('data-opt'))]; if (t) { S.pending = plan; chooseTarget(t); }
            return;
        }
        if (act === 'findnum') { try { A().findNumbers(); toast('Looking for your numbers and sponsors — about 40 seconds. Then say what you want for them.'); } catch (e) {} clearInput(); render(); return; }
        if (act === 'help') { S.help = !S.help; S.selectPrompt = null; render(); return; }
        if (act === 'startyes') { S.confirmStart = false; try { A().startOver(); } catch (e) {} S.feed = []; S.last = null; render(); return; }
        if (act === 'startno') { S.confirmStart = false; render(); return; }
        var recEl = closestAttr(el, ['data-rec'], _dock), rec = null;
        if (recEl) { var rid = Number(recEl.getAttribute('data-rec')); S.feed.forEach(function (r) { if (r.id === rid) rec = r; }); }
        if (rec && act === 'undo') { undoRec(rec); return; }
        if (rec && act === 'next') { rerun(rec, 1); return; }
        if (rec && act === 'prev') { rerun(rec, -1); return; }
    }

    // "/" jumps to the bar from anywhere in Easy; Esc leaves it
    function onGlobalKey(ev) {
        if (ev.key !== '/' || ev.ctrlKey || ev.metaKey || ev.altKey) return;
        var t = ev.target, tag = t && t.tagName ? t.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || (t && t.isContentEditable)) return;
        if (!ready() || !_input) return;
        ev.preventDefault(); ev.stopPropagation(); _input.focus(); _input.select();
    }

    // ------------------------------------------------------------ boot
    function paintKeyNow() { var pf = ''; try { pf = String((($('paintFile') || {}).value) || ''); } catch (e) {} return pf; }
    function tick() {
        var pk = paintKeyNow();
        if (S.paintKey !== null && pk !== S.paintKey) { S.feed = []; S.last = null; S.lastRecipe = null; S.pending = null; S.selectPrompt = null; S.plan = null; S.seed = Math.floor(Math.random() * 6); if (_input) _input.value = ''; S.phrase = ''; }
        S.paintKey = pk;
        var show = ready();
        if (show && !$('spbEasyTell')) { _dock = null; render(); }
        else if ($('spbEasyTell')) { $('spbEasyTell').hidden = !show; if (show && !S.phrase.trim() && !S.focus) render(); }
    }
    function boot() {
        var a = A();
        if (a && typeof a.onRail === 'function' && typeof a.batch === 'function') {
            a.onRail(function () { try { tick(); } catch (e) {} });
            setInterval(function () { try { tick(); } catch (e) {} }, 1600);
            _tipTimer = setInterval(function () { try { rotatePlaceholder(); } catch (e) {} }, 5200);
            document.addEventListener('keydown', onGlobalKey, true);
            try { tick(); } catch (e2) {}
            return;
        }
        if (!document.getElementById('spbEasyRoot') && (boot._n = (boot._n || 0) + 1) > 60) return;
        setTimeout(boot, 800);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 1500); });
    else setTimeout(boot, 1500);

    // Small public surface for tests / other Easy modules.
    window.spbEasyTell = {
        say: function (phrase) { if (_input) _input.value = phrase; S.phrase = String(phrase || ''); submit(S.phrase); return S.feed[0] || null; },
        parse: function (phrase) { return parseNow(phrase); },
        state: function () { return S; },
        focus: function () { if (_input) _input.focus(); },
        prefill: function (text) {                                   // the LAYERS panel's ✦: put words in the bar, focus it, show what they mean so far
            if (!ensureDock() || !_input) return;
            _input.value = String(text || ''); S.phrase = _input.value; S.selectPrompt = null; S.help = false;
            try { S.plan = S.phrase.trim() ? parseNow(S.phrase) : null; S.planFor = S.phrase; } catch (e) { S.plan = null; }
            render(); _input.focus(); try { var n = _input.value.length; _input.setSelectionRange(n, n); } catch (e2) {}
        },
        render: render,
        world: world
    };
})();
