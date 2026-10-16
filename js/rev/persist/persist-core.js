/* [SPB-PERSIST-ALL 2026-10-10 lane PERSIST-ALL] ONE shared persistence registry for the tools made on 2026-10-09/10.
 *
 * WHY: each new tool kept its state in a different place (Fade/Wear only in the project file; layer materials, Number Kit and Sponsor Kit only on the
 * layer, so a crash checkpoint dropped them; Edge Bleed in a local pref the project never saw). The measured matrix is in
 * _easy_claude_work/rev_tools/persist/MATRIX.md (before -> after, per tool x {Save/Open, reload, crash, undo}).
 *
 * WHAT (all additive, nothing existing is rewritten):
 *   SPB_PERSIST.register(name, {save, load, empty, listen|sig, project, autosave})   a document-level tool (Fade, Wear, Edge Bleed...)
 *       - autosave: saved to IndexedDB 'spb_persist_all_v1' on every change (key 'tool:<name>', tagged with the source fingerprint);
 *         restored once when the SAME source loads again (reload or crash) if the tool is still empty.
 *       - project: true  -> also written into the project file under persist.tools.<name> (restoreProject puts it back).
 *   SPB_PERSIST.registerLayer(name, {save(layer), load(layer, rec), sig(layer)})        state that rides on a layer (layer material, Number Kit, Sponsor Kit)
 *       - saved per layer next to the crash checkpoint ('layerx:<session>:<layerId>'); tfx3-layerrecovery.js prepare() asks prepareRecovery(la)
 *         for one extra sentence in the single restore prompt and applies the extras together with the layers (so Ctrl+Z undoes them with the layers).
 *   Old projects / autosaves: no existing key or field changes; a project without persist{} opens exactly as before.
 *
 * MEASURED (rev_tools/persist/MATRIX.md, ARCA PSD 23 layers, real crash): crash recovery lost 5 of 14 tools (layer materials + Autopilot results, Number Kit, Sponsor Kit, Fade, Wear) -> 0; project Save/Open lost 1 (Edge Bleed) -> 0; clean reload: Fade/Wear use the same restore path as the crash cell (reload cell NOT re-measured after the change: two harness timeouts; layer-level tools stay lost on a clean close by policy).
 *
 * KILL SWITCH: window.SPB_PERSIST_ALL_OFF = true, or localStorage SPB_PERSIST_ALL_OFF = '1'  ->  registry inert (no timers, no IndexedDB, collect() null,
 *              prepareRecovery() null) = the behaviour before this lane, byte for byte.
 */
(function (root) {
    'use strict';
    if (!root || root.SPB_PERSIST) return;
    var VER = 'persist-1.0';
    var DB_NAME = 'spb_persist_all_v1', STORE = 'kv', TICK_MS = 1500;
    var doc = root.document;

    function off() {
        try { if (root.SPB_PERSIST_ALL_OFF) return true; } catch (_) { }
        try { return root.localStorage.getItem('SPB_PERSIST_ALL_OFF') === '1'; } catch (_) { return false; }
    }
    function sh(s) { s = String(s); var h = 0x811c9dc5; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
    function jstr(v) { try { return JSON.stringify(v === undefined ? null : v); } catch (_) { return 'x' + Math.random(); } }
    function toast(msg, warn) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!warn); } catch (_) { } }
    function stack() { try { return (typeof root._psdLayers !== 'undefined' && Array.isArray(root._psdLayers)) ? root._psdLayers : (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers) ? _psdLayers : []); } catch (_) { return []; } }

    // ------------------------------------------------------------------ IndexedDB (own database; the tfx3 / material databases are never touched)
    var dbp = null;
    function openDb() {
        if (dbp) return dbp;
        dbp = new Promise(function (resolve, reject) {
            try {
                var rq = root.indexedDB.open(DB_NAME, 1);
                rq.onupgradeneeded = function () { try { rq.result.createObjectStore(STORE, { keyPath: 'key' }); } catch (_) { } };
                rq.onsuccess = function () { resolve(rq.result); };
                rq.onerror = function () { reject(rq.error || new Error('idb open failed')); };
                rq.onblocked = function () { reject(new Error('idb blocked')); };
            } catch (e) { reject(e); }
        });
        dbp.catch(function () { dbp = null; });
        return dbp;
    }
    function txDone(tx) { return new Promise(function (res, rej) { tx.oncomplete = function () { res(true); }; tx.onerror = function () { rej(tx.error || new Error('idb tx')); }; tx.onabort = function () { rej(tx.error || new Error('idb abort')); }; }); }
    function reqP(rq) { return new Promise(function (res, rej) { rq.onsuccess = function () { res(rq.result); }; rq.onerror = function () { rej(rq.error); }; }); }
    async function kvPut(recs) { var db = await openDb(), tx = db.transaction(STORE, 'readwrite'), os = tx.objectStore(STORE); recs.forEach(function (r) { os.put(r); }); return txDone(tx); }
    async function kvDel(keys) { if (!keys.length) return true; var db = await openDb(), tx = db.transaction(STORE, 'readwrite'), os = tx.objectStore(STORE); keys.forEach(function (k) { os.delete(k); }); return txDone(tx); }
    async function kvGet(key) { var db = await openDb(); return reqP(db.transaction(STORE, 'readonly').objectStore(STORE).get(key)); }
    async function kvAll() { var db = await openDb(); return reqP(db.transaction(STORE, 'readonly').objectStore(STORE).getAll()); }

    // ------------------------------------------------------------------ state
    var TOOLS = {};      // document-level tools
    var LAYER = {};      // layer-attached tools
    var S = {
        fp: '', retry: null, promptSeen: false, accepted: false, openBusy: 0, deciding: false, timer: 0, started: false, dirty: {}, written: {}, lastLayerSig: '', layerKeys: {},
        log: [], restored: {}, errors: [], writes: 0, ticks: 0
    };
    function log(m) { S.log.push(new Date().toISOString().slice(11, 19) + ' ' + m); if (S.log.length > 60) S.log.shift(); }
    function err(where, e) { S.errors.push(where + ': ' + String(e && e.message || e)); if (S.errors.length > 20) S.errors.shift(); }

    function register(name, spec) {
        if (!name || !spec || typeof spec.save !== 'function' || typeof spec.load !== 'function') return false;
        TOOLS[name] = spec; spec._name = name;
        if (typeof spec.listen === 'function') { try { spec.listen(function () { S.dirty[name] = true; }); } catch (e) { err('listen ' + name, e); } }
        return true;
    }
    function registerLayer(name, spec) {
        if (!name || !spec || typeof spec.save !== 'function' || typeof spec.load !== 'function') return false;
        LAYER[name] = spec; spec._name = name; return true;
    }

    // ------------------------------------------------------------------ identity of the loaded source (same string the crash checkpoint uses)
    function currentFp() {
        try { var t3 = root.SPBTfx3Recovery; if (t3 && !root.SPB_TFX3_OFF && t3.active() && t3.fingerprint()) return String(t3.fingerprint()); } catch (_) { }
        try { if (typeof root._spbLayerSourceFingerprint === 'function') return String(root._spbLayerSourceFingerprint() || ''); } catch (_) { }
        try { if (typeof _spbLayerSourceFingerprint === 'function') return String(_spbLayerSourceFingerprint() || ''); } catch (_) { }
        return '';
    }
    function sessionId() { try { return String(typeof _spbLayerAutosaveSessionId !== 'undefined' ? _spbLayerAutosaveSessionId : (root._spbLayerAutosaveSessionId || '')); } catch (_) { return ''; } }
    function checkpointSession() { try { var r = root.localStorage.getItem('shokker_layer_autosave'); return r ? String((JSON.parse(r) || {}).sessionId || '') : ''; } catch (_) { return ''; } }
    function recoveryPending() { try { return !!(root.SPBTfx3Recovery && root.SPBTfx3Recovery.pending && root.SPBTfx3Recovery.pending()); } catch (_) { return false; } }

    // ------------------------------------------------------------------ document-level tools: autosave + restore-on-load
    function emptyOf(t) { try { return typeof t.empty === 'function' ? !!t.empty() : true; } catch (_) { return true; } }
    async function restoreGlobals(fp, only, viaCrash) {
        var done = [], failed = [], joined = 0;
        for (var name in TOOLS) {
            var t = TOOLS[name]; if (t.autosave === false) continue;
            if (only && only.indexOf(name) < 0) continue;
            if (viaCrash && SES && SES.undone) { log('skipped ' + name + ': the painter already took the restored session back'); continue; }   // [POLISH-I item 2]
            try {
                var rec = await kvGet('tool:' + name);
                if (!rec || rec.fp !== fp || !rec.data) continue;
                if (!emptyOf(t)) continue;                       // the painter (or a project) already has this tool in use: never overwrite
                var r = await t.load(rec.data);
                if (r && r.ok === false) { err('restore ' + name, r.why || 'not ok'); failed.push(name); continue; }
                S.restored[name] = Date.now(); done.push(t.label || name);
                if (viaCrash && sessionJoin(name)) joined++;    // [POLISH-I item 2] one undo step with the layers
                log('restored ' + name + ' for ' + fp.slice(0, 40));
            } catch (e) { err('restore ' + name, e); failed.push(name); }
        }
        if (done.length) toast('Restored your ' + done.join(' and ') + ' from your last session.' + (joined ? ' Ctrl+Z takes the restored session back.' : ''));
        S.retry = failed.length ? { names: failed, left: (only ? (S.retry ? S.retry.left : 3) : 3) - (only ? 1 : 0), crash: !!viaCrash } : null;   // up to 3 more tries (the car model may still be loading)
        return done;
    }
    async function saveGlobals(fp) {
        var recs = [];
        for (var name in TOOLS) {
            var t = TOOLS[name]; if (t.autosave === false) continue;
            if (S.retry && S.retry.left > 0 && S.retry.names.indexOf(name) >= 0) continue;   // never overwrite a record that is still waiting to be restored
            var sig = null;
            try { if (typeof t.sig === 'function') sig = String(t.sig()); } catch (_) { sig = null; }
            if (!(S.dirty[name] || (sig !== null && sig !== S.written[name]))) continue;
            var data = null;
            try { data = t.save(); } catch (e) { err('save ' + name, e); continue; }
            var tag = sig !== null ? sig : sh(jstr(data));
            if (S.written[name] === tag && !S.dirty[name]) continue;
            S.dirty[name] = false;
            recs.push({ key: 'tool:' + name, fp: fp, ts: Date.now(), data: data || null });
            S.written[name] = tag;
        }
        if (recs.length) { await kvPut(recs); S.writes += recs.length; log('saved ' + recs.map(function (r) { return r.key + (r.data ? '' : '(empty)'); }).join(',')); }
    }

    // ------------------------------------------------------------------ layer-attached tools: written next to the crash checkpoint
    function layerSig(l) {
        var out = [];
        for (var n in LAYER) { var s = ''; try { s = String(LAYER[n].sig ? LAYER[n].sig(l) : sh(jstr(LAYER[n].save(l)))); } catch (_) { s = ''; } if (s) out.push(n + '=' + s); }
        return out.join(';');
    }
    async function saveLayers() {
        var sid = sessionId(); if (!sid) return;
        var ls = stack(), sigs = [], rows = [], keep = {};
        for (var i = 0; i < ls.length; i++) {
            var l = ls[i], s = layerSig(l); if (!s) continue;
            sigs.push(String(l.id) + '~' + s); keep['layerx:' + sid + ':' + l.id] = { l: l, s: s };
        }
        var all = sigs.join('|');
        if (all === S.lastLayerSig) return;
        S.lastLayerSig = all;
        for (var k in keep) {
            var item = keep[k], l2 = item.l, ext = {}, any = false;
            for (var n in LAYER) { try { var v = LAYER[n].save(l2); if (v !== undefined && v !== null) { ext[n] = v; any = true; } } catch (e) { err('layer save ' + n, e); } }
            if (any) rows.push({ key: k, session: sid, id: String(l2.id), name: l2.name || '', path: l2.path || '', ts: Date.now(), ext: ext });
        }
        var gone = Object.keys(S.layerKeys).filter(function (k) { return !keep[k]; });   // a layer that lost its extras (or was deleted) must not come back
        S.layerKeys = {}; Object.keys(keep).forEach(function (k) { S.layerKeys[k] = 1; });
        if (rows.length) { await kvPut(rows); S.writes += rows.length; }
        if (gone.length) await kvDel(gone);
        log('layer extras: ' + rows.length + ' kept, ' + gone.length + ' dropped');
    }
    async function purgeOldSessions() {
        try {
            var cur = sessionId(), cp = checkpointSession(), rows = await kvAll(), del = [];
            rows.forEach(function (r) { if (r && typeof r.key === 'string' && r.key.indexOf('layerx:') === 0 && r.session !== cur && r.session !== cp) del.push(r.key); });
            if (del.length) await kvDel(del);
        } catch (e) { err('purge', e); }
    }

    // ------------------------------------------------------------------ crash recovery hook (called by js/canvas/tfx3-layerrecovery.js prepare())
    var KIND_LABEL = { layermat: ['layer material', 'layer materials'], numbers: ['Number Kit layer', 'Number Kit layers'], sponsor: ['Sponsor Kit layer', 'Sponsor Kit layers'] };

    // [TICKETS-3 2026-10-10 item 3, IQ3-6] the prompt only promised "layer order, visibility and opacity come back" while Restore also brings back the brush coats, Race Wear,
    // Car-Space Fade and the Spec Sculpt look, and Start Fresh clears exactly those but KEEPS the zones (they restore from their own autosave, before the painter answers).
    // The line is now written from what this car really has saved: what comes back, then "Your zones stay either way. Start Fresh clears ...". Only tools that exist are named.
    // Kill switch: window.SPB_T3_OFF or SPB_T3_3_OFF (the line is then as before: kits only).
    function t3off(n) { try { return !!(root.SPB_T3_OFF || root['SPB_T3_' + n + '_OFF']); } catch (_) { return false; } }
    function joinAnd(a) { return a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }
    async function savedTools(la) {
        var inv = { coats: false, spec: false, wear: false, fade: false };
        try {   // brush coats + the spec layer (Spec Sculpt / spec strokes) + brushed paint: REV-MATERIAL keeps its own record per car (and may already have put it back)
            var MP = root.SPBRevMaterialPersist, M = root.SPBRevMaterial, rec = null;
            if (MP && MP.keyOf && MP.sourcePath && MP.get) { var k = MP.keyOf(MP.sourcePath()); rec = k ? await MP.get(k) : null; }
            var d = rec && rec.data;
            if (d) { inv.coats = !!((d.coats && d.coats.length) || d.paint); inv.spec = !!d.spec; }
            if (M && typeof M.stats === 'function' && !M.isEmpty()) { var st = M.stats(); if (st.coats && st.coats.length) inv.coats = true; if (st.hasSpec) inv.spec = true; if (st.hasPaint) inv.coats = true; }
        } catch (e) { err('prompt material', e); }
        try {   // Race Wear / Car-Space Fade: their autosave record for this car's fingerprint
            var fps = [la && la.sourceFingerprint, currentFp()].filter(Boolean).map(String);
            var names = ['wear', 'fade'];
            for (var i = 0; i < names.length; i++) { var r = await kvGet('tool:' + names[i]); if (r && r.data && fps.indexOf(String(r.fp)) >= 0) inv[names[i]] = true; }
        } catch (e) { err('prompt tools', e); }
        return inv;
    }
    function promptLine(base, inv) {
        var back = [], clr = [];
        if (inv.coats) { back.push('brush coats'); clr.push('brush coats'); }
        if (inv.wear) { back.push('Race Wear'); clr.push('wear'); }
        if (inv.fade) { back.push('Car-Space Fade'); clr.push('fade'); }
        if (inv.spec) { back.push('Spec Sculpt look'); clr.push('Spec Sculpt'); }
        var out = [];
        if (base) out.push(base);
        if (back.length) out.push('Your ' + joinAnd(back) + (back.length === 1 && back[0] !== 'brush coats' ? ' comes' : ' come') + ' back too.');
        out.push('Your zones stay either way.' + (clr.length ? ' Start Fresh clears ' + joinAnd(clr) + '.' : ''));
        return out.join(' ');
    }
    async function prepareRecovery(la) {
        if (off() || !la || !la.sessionId) return null;
        S.promptSeen = true; S.accepted = false;      // the painter is being asked: "Start Fresh" must also leave Fade / Wear alone (see tick)
        var rows = [];
        try { rows = (await kvAll()).filter(function (r) { return r && typeof r.key === 'string' && r.key.indexOf('layerx:' + la.sessionId + ':') === 0 && r.ext; }); } catch (e) { err('prepare', e); rows = []; }
        var inv3 = null; if (!t3off(3)) { try { inv3 = await savedTools(la); } catch (e) { err('prompt inv', e); inv3 = null; } }
        if (!rows.length) return { line: inv3 ? promptLine('', inv3) : '', rows: 0, apply: function () { S.accepted = true; sessionBegin(); return { n: 0, byTool: {} }; } };
        var count = {};
        rows.forEach(function (r) { for (var n in r.ext) count[n] = (count[n] || 0) + 1; });
        var bits = [];
        Object.keys(count).forEach(function (n) { var lab = KIND_LABEL[n] || [n, n]; bits.push(count[n] + ' ' + (count[n] === 1 ? lab[0] : lab[1])); });
        var line = bits.length ? (bits.join(', ').replace(/, ([^,]*)$/, ' and $1') + (rows.length === 1 && bits.length === 1 && count[Object.keys(count)[0]] === 1 ? ' also comes' : ' also come') + ' back with ' + (rows.length === 1 ? 'its' : 'their') + ' settings.') : '';
        if (inv3) line = promptLine(line, inv3);
        return {
            line: line, rows: rows.length,
            apply: function () {
                S.accepted = true;
                var ls = stack(), n = 0, applied = {};
                rows.forEach(function (r) {
                    var l = ls.find(function (x) { return String(x.id) === String(r.id); })
                        || ls.find(function (x) { return r.path && x.path === r.path && x.name === r.name; })
                        || ls.find(function (x) { return x.name === r.name; });
                    if (!l) return;
                    for (var name in r.ext) { try { if (LAYER[name]) { LAYER[name].load(l, r.ext[name]); applied[name] = (applied[name] || 0) + 1; n++; } } catch (e) { err('layer load ' + name, e); } }
                });
                try { if (typeof root.renderLayerPanel === 'function') root.renderLayerPanel(); } catch (_) { }
                try { var M = root.SPBRevLayerMat; if (M && typeof M.noticeChange === 'function') M.noticeChange(true); } catch (_) { }
                S.lastLayerSig = '';      // next tick re-writes under the new session id
                sessionBegin();           // [POLISH-I item 2] the "Restored session" undo step (right above the loader's layer step)
                log('recovery applied ' + jstr(applied));
                return { n: n, byTool: applied };
            }
        };
    }

    // ------------------------------------------------------------------ project Save / Open
    function collect() {
        if (off()) return null;
        var tools = {}, any = false;
        for (var name in TOOLS) {
            var t = TOOLS[name]; if (t.project !== true) continue;      // 'legacy' = already carried by its own project field
            try { var v = t.save(); if (v !== undefined) { tools[name] = v; any = true; } } catch (e) { err('collect ' + name, e); }
        }
        return any ? { v: 1, tools: tools } : null;
    }
    async function restoreProject(obj) {
        if (off() || !obj || typeof obj !== 'object' || !obj.tools) return { ok: true, n: 0 };     // old project: nothing to do, nothing changes
        var n = 0, bad = [];
        for (var name in obj.tools) {
            var t = TOOLS[name]; if (!t || t.project !== true) continue;
            try { var r = await t.load(obj.tools[name]); if (r && r.ok === false) bad.push(name); else n++; } catch (e) { bad.push(name); err('project load ' + name, e); }
        }
        return { ok: !bad.length, n: n, bad: bad };
    }
    // a project open owns the document-level tools: the autosave must neither restore over it nor decide against it
    function openBegin() { S.openBusy++; }
    function openEnd() { S.openBusy = Math.max(0, S.openBusy - 1); if (!S.openBusy) { S.fp = currentFp(); S.lastLayerSig = ''; for (var n in TOOLS) { S.written[n] = undefined; S.dirty[n] = true; } } }   // the opened document's tool state (empty or not) becomes the new autosave

    // [LEFTOVERS-3 item 2, 2026-10-10] "Start Fresh" on the crash prompt must also empty the tools that restore THEMSELVES from their own autosave (Material /
    // Spec Sculpt: REV-MATERIAL-2 puts its strokes + spec layer back as soon as the source loads, before the painter has even answered). A tool opts in with a
    // declined() hook; it runs once when the painter declines. Measured before: layers 15 -> 13 but the Spec Sculpt spec layer (crc 54a6ca55) stayed on the car.
    // Kill switch: window.SPB_LO3_OFF, or window.SPB_LO3_2_OFF.
    function lo3off(n) { try { return !!(root.SPB_LO3_OFF || root['SPB_LO3_' + n + '_OFF']); } catch (_) { return false; } }
    function declineTools() {
        if (lo3off(2)) return;
        for (var name in TOOLS) {
            var t = TOOLS[name]; if (typeof t.declined !== 'function') continue;
            try { t.declined(); log('declined: emptied ' + name); } catch (e) { err('declined ' + name, e); }
        }
    }

    // ------------------------------------------------------------------ [POLISH-I 2026-10-10 item 2] "Restored session": ONE undo step for everything a crash restore brings back
    // BEFORE (LEFTOVERS-3 measured, ARCA PSD, real crash, answered "Restore Session"): Ctrl+Z took the layers + their extras (Number Kit, Sponsor Kit, layer materials,
    // stripe, text, adjustments...) back in ONE step (the loader's "restore interrupted layer session" step) but Car-Space Fade, Race Wear and the Spec Sculpt look
    // (the REV-MATERIAL spec layer) stayed on the car: they were put back after / beside that step and were on no undo stack.
    // RULE (consistent with how every other restored item already behaves): what the painter ACCEPTS in the crash prompt is one undoable step. Anything a reload, a
    // project Open or Start Fresh brings back is the baseline (nothing to undo, as before; Start Fresh empties the tools, LEFTOVERS-3 item 2).
    // HOW: the loader pushes its layer step and then calls prepareRecovery().apply() in the same synchronous block, so a synthetic undo kind ('restored-session',
    // through the app's own SPBUndoExt registry, no core file touched) is recorded right above it. Tools that come back (Fade / Wear a tick later, the Spec Sculpt look
    // already on the car) join that record. Ctrl+Z on it empties those tools and then steps the layer step below it (one key press); Ctrl+Y puts both back.
    // Kill switch: window.SPB_POLISH_I_OFF, or window.SPB_POLISH_I_2_OFF (= the behaviour before this lane).
    var KIND = 'restored-session', SES = null;   // SES = { tools: {name: {after}}, layerBelow, undone, busy }
    function piOff(n) { try { return !!(root.SPB_POLISH_I_OFF || (n && root['SPB_POLISH_I_' + n + '_OFF'])); } catch (_) { return false; } }
    function sesExt() { var U = root.SPBUndoExt; return (!piOff(2) && U && typeof U.register === 'function' && typeof root._recordUndoAction === 'function') ? U : null; }
    function histTop(n) { try { var h = typeof root.getUnifiedUndoHistoryEntries === 'function' ? root.getUnifiedUndoHistoryEntries(n || 2) : null; return Array.isArray(h) ? h : []; } catch (_) { return []; } }
    function isLayerRestoreStep(e) { return !!(e && e.kind === 'layer' && /interrupted layer session/i.test(String(e.label || ''))); }
    function sesTools() { return SES ? Object.keys(SES.tools) : []; }
    function sesUndo() {
        var s = SES; if (!s || s.undone || s.busy) return false;
        s.busy = true;
        try {
            sesTools().forEach(function (n) {
                var t = TOOLS[n]; if (!t) return;
                try { var cur = t.save(); s.tools[n].after = (cur === undefined ? null : cur); } catch (e) { err('session save ' + n, e); }   // exactly what Ctrl+Y must bring back
                try { var r = t.load(null); if (r && typeof r.catch === 'function') r.catch(function (e) { err('session clear ' + n, e); }); } catch (e) { err('session clear ' + n, e); }
            });
            s.undone = true;
            // the loader's layer step sits right below this one (the history view still lists this entry on top while we run): same key press takes it back
            var h = histTop(2);
            if (s.layerBelow && isLayerRestoreStep(h[1]) && typeof root.undoDrawStroke === 'function') root.undoDrawStroke();
            log('session undone: ' + sesTools().join(',') + (s.layerBelow ? ' + layers' : ''));
        } catch (e) { err('session undo', e); } finally { s.busy = false; }
        try { if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) { }
        return true;
    }
    function sesRedo() {
        var s = SES; if (!s || !s.undone || s.busy) return false;
        s.busy = true;
        try {
            if (s.layerBelow && typeof root.redoDrawStroke === 'function') root.redoDrawStroke();
            sesTools().forEach(function (n) {
                var t = TOOLS[n], d = s.tools[n] && s.tools[n].after; if (!t || d === undefined || d === null) return;
                try { var r = t.load(d); if (r && typeof r.catch === 'function') r.catch(function (e) { err('session redo ' + n, e); }); } catch (e) { err('session redo ' + n, e); }
            });
            s.undone = false;
            log('session redone: ' + sesTools().join(',') + (s.layerBelow ? ' + layers' : ''));
        } catch (e) { err('session redo', e); } finally { s.busy = false; }
        try { if (typeof root.triggerPreviewRender === 'function') root.triggerPreviewRender(); } catch (_) { }
        return true;
    }
    var sesReg = false;
    function sesRegister(U) {
        if (sesReg) return;
        U.register(KIND, {
            hasUndo: function () { return !!(SES && !SES.undone); },
            hasRedo: function () { return !!(SES && SES.undone); },
            undo: sesUndo, redo: sesRedo,
            clearRedo: function () { if (SES && SES.undone && !SES.busy) SES = null; },   // a new action ends the redo branch: this restore can no longer be put back
            label: function () { return 'Restored session'; }
        });
        sesReg = true;
    }
    // called by prepareRecovery().apply() in the same synchronous block as the loader's layer step; layerBelow only when that step really is on top of the history
    function sessionBegin() {
        var U = sesExt(); if (!U) return false;
        try {
            sesRegister(U);
            var top = histTop(1)[0];
            SES = { tools: {}, layerBelow: isLayerRestoreStep(top), undone: false, busy: false, at: Date.now() };
            var m = TOOLS.material;
            if (m && m.undoable && !emptyOf(m)) SES.tools.material = {};   // the Spec Sculpt look / brushed strokes put themselves back as soon as the source loaded: they are part of the restore
            root._recordUndoAction(KIND);
            log('session begun (layerBelow ' + SES.layerBelow + (SES.tools.material ? ', material' : '') + ')');
            return true;
        } catch (e) { err('session begin', e); SES = null; return false; }
    }
    function sessionJoin(name) {   // a tool restored by the autosave after an accepted crash prompt
        if (!SES || SES.undone || !TOOLS[name] || !TOOLS[name].undoable) return false;
        SES.tools[name] = SES.tools[name] || {};
        return true;
    }

    // ------------------------------------------------------------------ the poller
    async function tick() {
        if (off()) return;
        S.ticks++;
        try {
            if (S.openBusy || S.deciding) return;
            var fp = currentFp();
            if (fp && fp !== S.fp) {
                if (recoveryPending()) return;                    // the crash prompt (or the flat-file offer) is open: decide after the painter has answered
                var declined = S.promptSeen && !S.accepted;       // "Start Fresh": the interrupted session is NOT brought back, Fade / Wear included
                var viaCrash = S.promptSeen && S.accepted;        // [POLISH-I item 2] accepted in the crash prompt: what comes back joins the "Restored session" undo step
                S.promptSeen = false; S.accepted = false;
                if (!declined) {
                    S.deciding = true;
                    try { await restoreGlobals(fp, undefined, viaCrash); } finally { S.deciding = false; }
                } else { log('declined interrupted session: document-level tools not restored'); declineTools(); }
                S.fp = fp; for (var n in TOOLS) S.written[n] = undefined;
                purgeOldSessions();
                return;
            }
            if (fp && fp === S.fp && S.retry) {
                if (S.retry.left > 0) { S.deciding = true; try { await restoreGlobals(fp, S.retry.names.slice(), !!S.retry.crash); } finally { S.deciding = false; } }
                else S.retry = null;
            }
            if (fp && fp === S.fp) await saveGlobals(fp);
            if (!recoveryPending()) { await saveLayers(); if (S.ticks % 40 === 0) purgeOldSessions(); }
        } catch (e) { err('tick', e); }
    }
    // [TICKETS-3 2026-10-10 item 3, IQ3-6] while the crash prompt is open the preview waits for the answer, and the empty preview said "Configure zones to see live preview"
    // over a zone list that was already full (the zones restore from their own autosave). It now says what is really going on, and puts the old text back afterwards.
    var PN = { orig: null };
    var PNOTE = 'Waiting for your answer to the restore question. Your zones are already here: the live preview draws as soon as you choose.';
    function previewNote() {
        if (t3off(3)) { var e0 = doc.getElementById('previewEmpty'); if (e0 && PN.orig !== null && e0.textContent === PNOTE) { e0.textContent = PN.orig; PN.orig = null; } return; }
        try {
            var e = doc.getElementById('previewEmpty'); if (!e) return;
            var zc = 0; try { zc = (typeof zones !== 'undefined' && zones && zones.length) || 0; } catch (_) { zc = 0; }
            if (recoveryPending() && zc > 0) { if (e.textContent !== PNOTE) { if (PN.orig === null) PN.orig = e.textContent; e.textContent = PNOTE; } }
            else if (PN.orig !== null && e.textContent === PNOTE) { e.textContent = PN.orig; PN.orig = null; }
        } catch (_) { }
    }
    function start() {
        if (S.started || off()) return; S.started = true;
        S.timer = setInterval(tick, TICK_MS);
        setInterval(previewNote, 400);
        try { doc.addEventListener('visibilitychange', function () { if (doc.visibilityState === 'hidden') tick(); }); } catch (_) { }
    }
    function flush() { return tick(); }

    // ------------------------------------------------------------------ adapters (resolved lazily: every tool script loads after this one)
    function installAdapters() {
        var R = root;
        register('fade', {
            label: 'Car-Space Fade', project: 'legacy', undoable: true,      // the project already carries revFade; autosave only; undoable = joins the "Restored session" step [POLISH-I item 2]
            listen: function (f) { if (R.SpbRevFadeUI && R.SpbRevFadeUI.on) R.SpbRevFadeUI.on(f); else throw new Error('fade not loaded'); },
            save: function () { return R.SpbRevFadeUI.serialize(); },
            load: function (o) { return R.SpbRevFadeUI.restore(o); },
            empty: function () { return !(R.SpbRevFadeUI.state.recs || []).length; }
        });
        register('wear', {
            label: 'Race Wear', project: 'legacy', undoable: true,
            listen: function (f) { if (R.SpbRevWearUI && R.SpbRevWearUI.on) R.SpbRevWearUI.on(f); else throw new Error('wear not loaded'); },
            save: function () { return R.SpbRevWearUI.serialize(); },
            load: function (o) { return R.SpbRevWearUI.restore(o); },
            empty: function () { return !R.SpbRevWearUI.serialize(); }
        });
        register('edgeBleed', {
            // [IQ2-5 2026-10-10, request from INTEGRATION-QA-2 via the coordinator] on/off + the bleed width were only in localStorage: a project opened on another machine or after
            // clearing site data came back different. Now the project carries them (persist.tools.edgeBleed = {on, px}); the local pref stays the default for new documents and
            // for old projects (no field = nothing changes, i.e. off unless this browser turned it on). autosave:false because the pref itself already survives a reload / crash.
            label: 'Edge Bleed', project: true, autosave: false,
            save: function () { var E = R.SpbRevSeam; if (!E || E.off()) return undefined; return { on: !!E.isOn(), px: E.px() }; },
            load: function (o) {
                var E = R.SpbRevSeam; if (!E || E.off() || !o || typeof o.on !== 'boolean') return { ok: true };
                var px = parseInt(o.px, 10); if (px >= 1 && px <= 64 && px !== E.px()) R.SPB_REV_SEAM_PX = px;
                if (E.isOn() !== o.on) E.setOn(o.on);
                return { ok: true };
            }
        });
        register('material', {
            label: 'Material strokes', project: 'legacy', autosave: false, undoable: true,    // REV-MATERIAL-2 already autosaves to its own IndexedDB (keyed by source file) and carries revMaterial in the project
            save: function () { return R.SPBRevMaterial ? R.SPBRevMaterial.serialize() : undefined; },
            load: function (o) { return R.SPBRevMaterial ? R.SPBRevMaterial.restore(o) : { ok: true }; },
            empty: function () { return !R.SPBRevMaterial || R.SPBRevMaterial.isEmpty(); },
            // [LEFTOVERS-3 item 2] Start Fresh: the Spec Sculpt look (the REV-MATERIAL spec layer) and any brushed strokes / wear of the interrupted session are NOT kept
            declined: function () {
                var M = R.SPBRevMaterial, MP = R.SPBRevMaterialPersist; if (!M || M.off()) return;
                if (MP && typeof MP.decline === 'function') MP.decline();         // drops the autosaved record of this car and stops a restore that is still waiting for the zones
                if (!M.isEmpty()) M.restore(null);                                 // empties the live state (the autosave then writes 'empty')
            }
        });
        registerLayer('layermat', {
            sig: function (l) { return l.spbMaterial ? sh(jstr(l.spbMaterial)) : ''; },
            save: function (l) { return R.SPBRevLayerMat && l.spbMaterial ? R.SPBRevLayerMat.serialize(l) : undefined; },
            load: function (l, rec) { if (R.SPBRevLayerMat) R.SPBRevLayerMat.deserialize(l, rec); }
        });
        registerLayer('numbers', {
            sig: function (l) { var p = R.SpbRevNumbers && R.SpbRevNumbers.kitOf(l); return p ? sh(jstr(p)) : ''; },
            save: function (l) { return R.SpbRevNumbers ? R.SpbRevNumbers.serialize(l) : undefined; },
            load: function (l, rec) { if (R.SpbRevNumbers) R.SpbRevNumbers.deserialize(l, rec); }
        });
        registerLayer('sponsor', {
            sig: function (l) { var p = R.SpbRevSponsor && R.SpbRevSponsor.kitOf(l); if (!p) return ''; var lg = R.SpbRevSponsor.logoOf(p.kid); return sh(jstr(p)) + (lg ? ':' + (lg.cleaned ? 1 : 0) + ':' + String(lg.name || '') : ''); },
            save: function (l) { return R.SpbRevSponsor ? R.SpbRevSponsor.serialize(l) : undefined; },
            load: function (l, rec) { if (R.SpbRevSponsor) R.SpbRevSponsor.deserialize(l, rec); }
        });
    }
    var tries = 0;
    function boot() {
        if (off()) return;
        var need = ['SpbRevFadeUI', 'SpbRevWearUI', 'SpbRevSeam', 'SPBRevLayerMat', 'SpbRevNumbers', 'SpbRevSponsor'];
        var ready = need.every(function (k) { return !!root[k]; });
        if (!ready && tries++ < 40) { setTimeout(boot, 500); return; }      // tools load later in the page; give up quietly after 20 s (the missing ones are simply not persisted)
        try { installAdapters(); } catch (e) { err('install', e); }
        start();
    }

    root.SPB_PERSIST = {
        version: VER, off: off, register: register, registerLayer: registerLayer, collect: collect, restoreProject: restoreProject, prepareRecovery: prepareRecovery,
        openBegin: openBegin, openEnd: openEnd, flush: flush, tick: tick,
        status: function () { return { version: VER, off: off(), fp: S.fp, tools: Object.keys(TOOLS), layerTools: Object.keys(LAYER), writes: S.writes, ticks: S.ticks, restored: Object.assign({}, S.restored), errors: S.errors.slice(), log: S.log.slice(-12), busy: S.openBusy, session: SES ? { tools: Object.keys(SES.tools), layerBelow: SES.layerBelow, undone: SES.undone } : null }; },
        _internal: { kvAll: kvAll, kvGet: kvGet, kvDel: kvDel, currentFp: currentFp, TOOLS: TOOLS, LAYER: LAYER }
    };
    if (doc) { if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot(); }
})(typeof window !== 'undefined' ? window : null);
