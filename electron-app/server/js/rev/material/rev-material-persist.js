/* [SPB-REV-MATERIAL 2026-10-10 / REV-MATERIAL-2] Autosave for brushed Material / Spec / Wear strokes.
 *
 * Project Save / Open carry the strokes in the project file itself (one optional field, see
 * js/features/spb-projects.js). This module is the crash / reload safety net:
 *  - every change (stroke, undo, redo, clear) is written 700 ms later to IndexedDB `spb_rev_material_v1`,
 *    keyed by the SOURCE PAINT FILE (so the strokes of car A never land on car B);
 *  - when the page comes back and the source paint finishes loading, that record is put back
 *    (only if nothing has been painted in between: live work is never overwritten);
 *  - switching to another source paint sets the old car's strokes aside (they stay in IndexedDB) and loads the
 *    new car's, if it has any;
 *  - at most 8 records are kept (newest wins); each record is the compact serialize() object (cropped PNGs).
 * Undo history is not saved: after a reload the history starts fresh.
 * Kill switch: SPB_REV_MAT_OFF (same as the tools) or window.SPB_REV_MAT_PERSIST_OFF = true / localStorage SPB_REV_MAT_PERSIST_OFF = '1'.
 */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    const M = root.SPBRevMaterial;
    if (!M || M.off()) return;
    const DB = 'spb_rev_material_v1', STORE = 'docs', KEEP = 8, SAVE_MS = 700;

    function offP() {
        if (root.SPB_REV_MAT_PERSIST_OFF || M.off()) return true;
        try { return root.localStorage.getItem('SPB_REV_MAT_PERSIST_OFF') === '1'; } catch (_) { return false; }
    }
    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (_) {} }

    // ---------------------------------------------------------------- IndexedDB
    let dbp = null;
    function db() {
        if (dbp) return dbp;
        dbp = new Promise(function (res, rej) {
            try {
                const r = root.indexedDB.open(DB, 1);
                r.onupgradeneeded = function () { if (!r.result.objectStoreNames.contains(STORE)) r.result.createObjectStore(STORE, { keyPath: 'key' }); };
                r.onsuccess = function () { res(r.result); };
                r.onerror = function () { rej(r.error); };
            } catch (e) { rej(e); }
        });
        dbp.catch(function () { dbp = null; });
        return dbp;
    }
    function tx(mode, fn) {
        return db().then(function (d) {
            return new Promise(function (res, rej) {
                const t = d.transaction(STORE, mode), st = t.objectStore(STORE);
                let out;
                try { out = fn(st); } catch (e) { rej(e); return; }
                t.oncomplete = function () { res(out && out.result !== undefined ? out.result : out); };
                t.onerror = function () { rej(t.error); };
                t.onabort = function () { rej(t.error || new Error('aborted')); };
            });
        });
    }
    const dbGet = function (key) { return tx('readonly', function (s) { return s.get(key); }); };
    const dbPut = function (rec) { return tx('readwrite', function (s) { return s.put(rec); }); };
    const dbDel = function (key) { return tx('readwrite', function (s) { return s.delete(key); }); };
    const dbAll = function () { return tx('readonly', function (s) { return s.getAll(); }); };
    function prune() {
        dbAll().then(function (all) {
            (all || []).sort(function (a, b) { return (b.savedAt || 0) - (a.savedAt || 0); }).slice(KEEP).forEach(function (r) { dbDel(r.key).catch(function () {}); });
        }).catch(function () {});
    }

    // ---------------------------------------------------------------- source key
    function sourcePath() {
        try { return typeof root.getCurrentSourcePaintFile === 'function' ? String(root.getCurrentSourcePaintFile() || '').trim() : ''; } catch (_) { return ''; }
    }
    function keyOf(p) { return String(p || '').trim().replace(/\//g, '\\').replace(/\\+/g, '\\').toLowerCase(); }

    const P = { cur: '', cand: '', dims: '', saveTimer: null, busy: false, lastSaved: '', log: [], skip: {} };
    function note(s) { P.log.push(new Date().toISOString().slice(11, 19) + ' ' + s); if (P.log.length > 40) P.log.shift(); }

    // ---------------------------------------------------------------- save
    function saveNow(forKey) {
        const key = forKey || P.cur;
        if (!key || offP()) return Promise.resolve(false);
        let data = null;
        try { data = M.serialize(); } catch (e) { console.warn('[REV-MATERIAL] autosave serialize', e); return Promise.resolve(false); }
        if (!data) {
            note('empty -> delete ' + key.slice(-40));
            P.lastSaved = key + '|empty';
            return dbDel(key).then(function () { return true; }).catch(function () { return false; });
        }
        const json = JSON.stringify(data.coats.map(function (c) { return c.id; })) + data.seq + (data.spec ? data.spec.val.length : 0);
        const rec = { key: key, source: sourcePath(), size: data.size, savedAt: Date.now(), data: data };
        note('save ' + key.slice(-40) + ' coats ' + data.coats.length + (data.spec ? ' spec' : '') + (data.paint ? ' paint' : ''));
        P.lastSaved = key + '|' + json;
        return dbPut(rec).then(function () { prune(); return true; }).catch(function (e) { console.warn('[REV-MATERIAL] autosave write', e); return false; });
    }
    function schedule() {
        if (offP() || !P.cur) return;
        if (P.saveTimer) clearTimeout(P.saveTimer);
        P.saveTimer = setTimeout(function () { P.saveTimer = null; saveNow(); }, SAVE_MS);
    }
    function flush() {
        if (P.saveTimer) { clearTimeout(P.saveTimer); P.saveTimer = null; saveNow(); }
    }

    // ---------------------------------------------------------------- restore
    function loadFor(key, tries) {
        if (offP() || !key) return;
        if (P.skip[key]) return;   // [LEFTOVERS-3 item 2] the painter chose "Start Fresh" for this car: nothing comes back
        const gen = M.state.gen;
        dbGet(key).then(function (rec) {
            if (!rec || !rec.data) { if (!tries) note('no saved strokes for ' + key.slice(-40)); return; }
            if (P.cur !== key) return;
            const d = M.canvasDims();
            if (!d[0] || rec.size[0] !== d[0] || rec.size[1] !== d[1]) {
                // the paint may still be loading at a different size: try again shortly
                if ((tries || 0) < 12) setTimeout(function () { loadFor(key, (tries || 0) + 1); }, 1000);
                else note('not restored: saved for a ' + rec.size.join('x') + ' sheet, this one is ' + d.join('x'));
                return;
            }
            if (M.state.gen !== gen || !M.isEmpty() || M.state.st) { note('restore skipped: live work exists'); return; }
            return M.restore(rec.data).then(function (r) {
                if (r && r.ok) {
                    note('restored ' + key.slice(-40) + ' coats ' + r.coats);
                    toast('Brushed material restored from your last session (' + describe(rec.data) + ').');
                } else if (r && r.why === 'zones not ready' && (tries || 0) < 12) setTimeout(function () { loadFor(key, (tries || 0) + 1); }, 1000);
                else note('restore failed: ' + (r && r.why));
            });
        }).catch(function (e) { console.warn('[REV-MATERIAL] autosave read', e); });
    }
    function describe(data) {
        const bits = [];
        if (data.coats && data.coats.length) bits.push(data.coats.length + ' finish' + (data.coats.length === 1 ? '' : 'es'));
        if (data.spec) bits.push('spec');
        if (data.paint) bits.push('wear');
        return bits.join(', ') || 'strokes';
    }

    // ---------------------------------------------------------------- source watcher
    function tick() {
        if (offP()) return;
        const p = sourcePath(), k = keyOf(p), d = M.canvasDims();
        if (!k || !d[0]) return;
        if (k === P.cur) {
            P.cand = '';
            // [REV-MATERIAL-2] the sheet changed size under the same source (the app names the car file before its paint has finished loading, the canvas is
            // a 300x150 blank until then): try the restore again for the new size, as long as nothing has been painted
            const ds = d[0] + 'x' + d[1];
            if (ds !== P.dims) { P.dims = ds; if (M.isEmpty() && !M.state.st) loadFor(k, 0); }
            return;
        }
        if (k !== P.cand) { P.cand = k; return; }   // act only when the new source is seen twice in a row (1 s apart)
        const old = P.cur;
        P.cur = k; P.cand = ''; P.dims = d[0] + 'x' + d[1];
        note('source ' + (old ? old.slice(-30) : '(none)') + ' -> ' + k.slice(-30));
        if (old && !M.isEmpty() && !M.state.st) {
            // the strokes belong to the car we just left: they are already saved under its key
            const done = P.saveTimer ? (clearTimeout(P.saveTimer), P.saveTimer = null, saveNow(old)) : Promise.resolve();
            done.then(function () {
                if (keyOf(sourcePath()) !== k) return;
                M.restore(null);
                toast('Material strokes stay with the previous car file. Open it again to get them back.');
                loadFor(k, 0);
            });
        } else {
            loadFor(k, 0);
            if (!M.isEmpty()) schedule();   // strokes painted before the source was adopted still get saved
        }
    }

    M.on(function (what) { if (what === 'changed') schedule(); });
    root.addEventListener('pagehide', flush);
    doc.addEventListener('visibilitychange', function () { if (doc.visibilityState === 'hidden') flush(); });
    setInterval(tick, 1000);

    // [LEFTOVERS-3 item 2, 2026-10-10] "Start Fresh" on the crash prompt: forget the saved strokes of the CURRENT car and never restore them in this page. New strokes
    // painted afterwards are saved as usual. Called by js/rev/persist/persist-core.js (material.declined).
    function decline(key) {
        const k = key || P.cur || keyOf(sourcePath());
        if (!k) return Promise.resolve(false);
        P.skip[k] = true; note('declined (Start Fresh) -> record dropped ' + k.slice(-40));
        if (P.saveTimer) { clearTimeout(P.saveTimer); P.saveTimer = null; }
        return dbDel(k).then(function () { return true; }).catch(function () { return false; });
    }

    root.SPBRevMaterialPersist = {
        decline: decline,
        saveNow: saveNow, flush: flush, loadFor: loadFor, tick: tick, state: P,
        all: function () { return dbAll(); }, get: dbGet, del: dbDel, keyOf: keyOf, sourcePath: sourcePath,
        // Project Open replaced the document: the autosave follows the project (also when it carries no strokes)
        adopt: function () { P.cur = keyOf(sourcePath()) || P.cur; P.cand = ''; schedule(); }
    };
})(typeof window !== 'undefined' ? window : null);
