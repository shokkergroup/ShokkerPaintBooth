/* [SPB-TFX3 2026-10-09 P1 crash recovery] Crash-recovery for ADDED layers (blank layers, live text, shapes, pastes, duplicates)
 * and for PAINTED source layers.
 *
 * BEFORE (measured, fix3/recovery_before.json): owner PSD (13 layers) + 1 added+painted layer + 1 live text layer, real
 * crash -> relaunch: 15 layers -> 13, both added layers gone, no recovery prompt at all. Two causes:
 *   1. the localStorage checkpoint stored layer SETTINGS only (pixelDataSaved:false) and its source fingerprint was taken over the
 *      WHOLE live stack, so one added layer made the fingerprint differ from the freshly imported PSD ("source fingerprint did
 *      not match" -> nothing applied, not even visibility/opacity of the 13 PSD layers);
 *   2. even with a matching fingerprint, added layers have no source to be matched to, so they were never re-created.
 *
 * AFTER: the fingerprint covers only the layers that came from the import, the checkpoint lists EVERY layer (id, added flag, order,
 * opacity, blend, lock, group info, text flag) and the pixels of every added layer plus every source layer whose img was replaced by
 * painting (canvas != the original import element) go to IndexedDB as PNG blobs (+ the live-text payload). Pixels never enter
 * localStorage (quota). Recovery is still ONE explicit confirm; Ctrl+Z undoes it.
 *
 * Kill switch: window.SPB_TFX3_OFF = true (or localStorage SPB_TFX3_OFF='1') -> the old settings-only behaviour, byte for byte.
 */
(function () {
    'use strict';
    if (window.SPBTfx3Recovery) return;
    try { if (window.SPB_TFX3_OFF !== true && localStorage.getItem('SPB_TFX3_OFF') === '1') window.SPB_TFX3_OFF = true; } catch (_e) { }

    var DB_NAME = 'spb_tfx3_layer_recovery_v1', STORE = 'kv';
    var MAX_BYTES = 400 * 1024 * 1024;      // total PNG bytes kept for recovery; beyond this the older record stays
    var QUIET_MS = 1500, MAX_WAIT_MS = 15000;

    var srcImg = null;                      // Map id -> the img element the import created (identity = "never painted")
    var srcFp = '';                         // source fingerprint of the freshly imported layer set (constant for the session: renames/paint/resizes of source layers must not change it)
    var persisted = {};                     // id -> { hash, w, h, bboxKey, td, bytes }
    var timer = 0, firstDirtyAt = 0, running = false, again = false, pendingRecovery = false;
    var st = { active: false, lastAt: 0, layers: 0, bytes: 0, error: null, runs: 0 };
    // [SPB-TFX4 2026-10-10 item 4 lane TOOLS-FIX-4] FLAT sources (TGA / PNG / JPEG, no layered document): every layer in the stack was added by the painter
    // (blank, text, paste, Smart-separate...), so ALL of them ride in the checkpoint with their pixels; identity = the flat file (path + content fingerprint,
    // or name|size|mtime for a picked file) + canvas size, prefixed "flat:". Additive: schema stays 3, PSD checkpoints and flat checkpoints can never match each other.
    var flatMode = false, flatTimer = 0;
    try { if (window.SPB_TFX4_OFF !== true && localStorage.getItem('SPB_TFX4_OFF') === '1') window.SPB_TFX4_OFF = true; } catch (_e4) { }

    function off() { return window.SPB_TFX3_OFF === true; }
    function off4() { return window.SPB_TFX4_OFF === true; }
    function stack() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : (window._psdLayers || []); }
    function sessionId() { try { return typeof _spbLayerAutosaveSessionId !== 'undefined' ? _spbLayerAutosaveSessionId : ''; } catch (_) { return ''; } }
    function srcFile() { try { return (typeof window.getCurrentSourcePaintFile === 'function') ? (window.getCurrentSourcePaintFile() || '') : ''; } catch (_) { return ''; } }
    function jclone(v) { try { return v == null ? v : JSON.parse(JSON.stringify(v)); } catch (_) { return undefined; } }
    function toast(m, kind) { try { if (typeof showToast === 'function') showToast(m, kind); } catch (_) { } }

    // ------------------------------------------------------------------ source identity
    var persistedMask = {}, persistedAdj = {};
    function reset() { srcImg = null; srcFp = ''; persisted = {}; persistedMask = {}; persistedAdj = {}; st.active = false; flatMode = false; if (flatTimer) { clearTimeout(flatTimer); flatTimer = 0; } }
    function markSource(layers, fp) {
        srcFp = fp || '';
        srcImg = new Map();
        (layers || []).forEach(function (l) { if (l && l.id != null) srcImg.set(String(l.id), l.img); });
        persisted = {}; st.active = !off();
    }
    function active() { return !off() && !!srcImg; }
    function isSource(l) { return !!srcImg && srcImg.has(String(l.id)); }
    function isModifiedSource(l) { return isSource(l) && srcImg.get(String(l.id)) !== l.img; }
    function sourceOnly(layers) { return srcImg ? (layers || []).filter(isSource) : layers; }
    function setPending(v) { pendingRecovery = !!v; if (!v) schedule('recovery-done'); }

    // adds the fields the checkpoint needs beyond the settings-only record
    function decorate(l, rec) {
        rec.id = String(l.id);
        rec.added = !isSource(l);
        rec.px = rec.added || isModifiedSource(l);
        rec.txt = !!(l.img && l.img.__spbText);
        rec.adj = !!(l.pcAdj && !window.SPB_TLAY_OFF);   // adjustment layers (SPBPcAdjust): the layer's own canvas is blank, the settings ride in an 'adj:' record
        rec.msk = !!(l.pcMask && !window.SPB_TLAY_OFF);   // [SPB-TFX3 2026-10-10 lane TOOLS-FIX-3, request from TOOLS-LAYERS] layer masks (SPBPcLayerMask) ride in IndexedDB 'mask:' records
        if (rec.added) {
            ['groupChain', 'parentGroupKey', 'rasterKey', 'pathParts', 'importVisible', 'ownVisible', 'elementLinkGroups', 'elementInstances'].forEach(function (k) {
                if (l[k] !== undefined) { var c = jclone(l[k]); if (c !== undefined) rec[k] = c; }
            });
        }
        return rec;
    }

    // ------------------------------------------------------------------ IndexedDB
    var dbp = null;
    function openDb() {
        if (dbp) return dbp;
        dbp = new Promise(function (resolve, reject) {
            try {
                var rq = indexedDB.open(DB_NAME, 1);
                rq.onupgradeneeded = function () { try { rq.result.createObjectStore(STORE, { keyPath: 'key' }); } catch (_) { } };
                rq.onsuccess = function () { resolve(rq.result); };
                rq.onerror = function () { reject(rq.error || new Error('idb open failed')); };
                rq.onblocked = function () { reject(new Error('idb blocked')); };
            } catch (e) { reject(e); }
        });
        dbp.catch(function () { dbp = null; });
        return dbp;
    }
    function txDone(tx) {
        return new Promise(function (res, rej) {
            tx.oncomplete = function () { res(true); };
            tx.onerror = function () { rej(tx.error || new Error('idb tx error')); };
            tx.onabort = function () { rej(tx.error || new Error('idb tx abort')); };
        });
    }
    async function writeAll(recs, keepIds, meta, keepMasks, keepAdj) {
        var db = await openDb(), tx = db.transaction(STORE, 'readwrite'), store = tx.objectStore(STORE), done = txDone(tx);
        recs.forEach(function (r) { store.put(r); });
        store.put(meta);
        var kq = store.getAllKeys();
        kq.onsuccess = function () {
            (kq.result || []).forEach(function (k) {
                if (typeof k !== 'string') return;
                if (k.indexOf('layer:') === 0 && !keepIds[k.slice(6)]) store.delete(k);
                else if (k.indexOf('mask:') === 0 && keepMasks && !keepMasks[k.slice(5)]) store.delete(k);
                else if (k.indexOf('adj:') === 0 && keepAdj && !keepAdj[k.slice(4)]) store.delete(k);
            });
        };
        await done;
    }
    async function readAll() {
        var db = await openDb(), tx = db.transaction(STORE, 'readonly'), store = tx.objectStore(STORE), done = txDone(tx), rq = store.getAll();
        await done;
        return rq.result || [];
    }

    // ------------------------------------------------------------------ pixels
    function snapshotCanvas(l) {
        var img = l && l.img; if (!img) return null;
        var w = img.naturalWidth || img.width || 0, h = img.naturalHeight || img.height || 0;
        if (!w || !h) return null;
        var c = document.createElement('canvas'); c.width = w; c.height = h;
        var x = c.getContext('2d', { willReadFrequently: true });
        try { x.drawImage(img, 0, 0); } catch (_) { return null; }
        return { canvas: c, ctx: x, w: w, h: h };
    }
    function hashSnap(s) {
        var d = new Uint32Array(s.ctx.getImageData(0, 0, s.w, s.h).data.buffer), hh = 0x811c9dc5 | 0, empty = true;
        for (var i = 0; i < d.length; i++) { var v = d[i]; if (v & 0xff000000) empty = false; hh = Math.imul(hh ^ v, 16777619); }
        return { hash: (hh >>> 0).toString(16) + ':' + s.w + 'x' + s.h, empty: empty };
    }
    function toBlob(c) { return new Promise(function (res) { try { c.toBlob(function (b) { res(b || null); }, 'image/png'); } catch (_) { res(null); } }); }

    // ------------------------------------------------------------------ persistence of the pixels (debounced, idle)
    function schedule(why) {
        if (!active()) return;
        var now = Date.now();
        if (!firstDirtyAt) firstDirtyAt = now;
        if (timer) clearTimeout(timer);
        timer = setTimeout(kick, (now - firstDirtyAt > MAX_WAIT_MS) ? 0 : QUIET_MS);
    }
    function kick() {
        timer = 0;
        if (!active()) return;
        if (pendingRecovery) { timer = setTimeout(kick, QUIET_MS); return; }
        var ft = false; try { ft = typeof freeTransformState !== 'undefined' && !!freeTransformState; } catch (_) { }
        if (ft) { timer = setTimeout(kick, QUIET_MS); return; }     // mid-transform the layer is lifted: wait for the commit
        if (running) { again = true; return; }
        firstDirtyAt = 0; running = true;
        var go = function () {
            persistNow().catch(function (e) { st.error = String(e && e.message || e); }).then(function () {
                running = false; if (again) { again = false; schedule('again'); }
            });
        };
        if (typeof requestIdleCallback === 'function') requestIdleCallback(go, { timeout: 4000 }); else go();
    }
    async function persistNow() {
        if (!active()) return false;
        var sess = sessionId(), file = flatSourceFile() || srcFile();   // [SPB-TFX4 item 4] flat session: the flat file's identity
        if (!sess || !file) return false;
        var layers = stack().slice(), cands = layers.filter(function (l) { return l && l.img && (!isSource(l) || isModifiedSource(l)); });
        var recs = [], keep = {}, next = {}, bytesTotal = 0, tooBig = false, hashed = 0;
        for (var i = 0; i < cands.length; i++) {
            var L = cands[i], id = String(L.id); keep[id] = 1;
            var snap = snapshotCanvas(L); if (!snap) continue;
            var hh = hashSnap(snap); hashed++;
            var bboxKey = Array.isArray(L.bbox) ? L.bbox.join(',') : '';
            var td = (L.img.__spbText) ? JSON.stringify(L.img.__spbText) : '';
            var prev = persisted[id];
            if (prev && prev.hash === hh.hash && prev.bboxKey === bboxKey && prev.td === td && prev.sess === sess) { next[id] = prev; bytesTotal += prev.bytes || 0; continue; }
            var blob = hh.empty ? null : await toBlob(snap.canvas);
            if (!hh.empty && !blob) { if (prev) { next[id] = prev; bytesTotal += prev.bytes || 0; } continue; }
            var bytes = blob ? blob.size : 0;
            bytesTotal += bytes;
            recs.push({ key: 'layer:' + id, id: id, sessionId: sess, w: snap.w, h: snap.h, bbox: Array.isArray(L.bbox) ? L.bbox.slice(0, 4) : [0, 0, snap.w, snap.h],
                hash: hh.hash, empty: hh.empty, blob: blob, textData: td ? JSON.parse(td) : null, savedAt: Date.now() });
            next[id] = { hash: hh.hash, bboxKey: bboxKey, td: td, bytes: bytes, sess: sess };
        }
        // layer masks: any layer (source or added) can carry one. The mask object is frozen and replaced on every edit (TOOLS-LAYERS), so reference inequality = changed.
        var keepMasks = {}, maskRecs = [], nextMask = {};
        if (!window.SPB_TLAY_OFF && window.SPBPcLayerMask && typeof window.SPBPcLayerMask.serialize === 'function') {
            layers.forEach(function (L) {
                if (!L || !L.pcMask) return;
                var mid = String(L.id), pm = persistedMask[mid];
                keepMasks[mid] = 1;
                if (pm && pm.ref === L.pcMask && pm.sess === sess) { nextMask[mid] = pm; bytesTotal += pm.bytes || 0; return; }
                var ser = null; try { ser = window.SPBPcLayerMask.serialize(L); } catch (_e) { }
                if (!ser) return;
                var mb = Math.round((ser.png ? ser.png.length : 0) * 0.75);
                bytesTotal += mb;
                maskRecs.push({ key: 'mask:' + mid, id: mid, sessionId: sess, pcMask: ser, savedAt: Date.now() });
                nextMask[mid] = { ref: L.pcMask, sess: sess, bytes: mb };
            });
        }
        var keepAdj = {}, adjRecs = [], nextAdj = {};
        if (!window.SPB_TLAY_OFF && window.SPBPcAdjust && typeof window.SPBPcAdjust.serialize === 'function') {
            layers.forEach(function (L) {
                if (!L || !L.pcAdj) return;
                var aid = String(L.id), pa = persistedAdj[aid];
                keepAdj[aid] = 1;
                if (pa && pa.ref === L.pcAdj && pa.sess === sess) { nextAdj[aid] = pa; return; }   // frozen object replaced on every edit: reference inequality = changed
                var sa = null; try { sa = window.SPBPcAdjust.serialize(L); } catch (_e) { }
                if (!sa) return;
                adjRecs.push({ key: 'adj:' + aid, id: aid, sessionId: sess, pcAdj: sa, savedAt: Date.now() });
                nextAdj[aid] = { ref: L.pcAdj, sess: sess };
            });
        }
        if (bytesTotal > MAX_BYTES) { tooBig = true; st.error = 'recovery pixels over ' + Math.round(MAX_BYTES / 1048576) + ' MB: older copy kept'; return false; }
        await writeAll(recs.concat(maskRecs, adjRecs), keep, { key: 'meta', sessionId: sess, sourcePaintFile: file, savedAt: Date.now(), ids: Object.keys(keep) }, keepMasks, keepAdj);
        persisted = next; persistedMask = nextMask; persistedAdj = nextAdj;
        st.lastAt = Date.now(); st.layers = Object.keys(keep).length; st.bytes = bytesTotal; st.error = null; st.runs++;
        try { window.__spbTfx3RecoveryStatus = Object.assign({}, st); } catch (_) { }
        return true;
    }
    function flush() { if (timer) { clearTimeout(timer); timer = 0; } return persistNow(); }

    // ------------------------------------------------------------------ recovery
    async function decode(rec) {
        var c = document.createElement('canvas'); c.width = rec.w; c.height = rec.h;
        if (rec.blob) {
            var bmp = await createImageBitmap(rec.blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
            // CPU-backed context = byte-exact round trip (a GPU-backed canvas premultiplies in float: +-1 on ~15 soft-edge pixels, measured)
            c.getContext('2d', { willReadFrequently: true }).drawImage(bmp, 0, 0);
            try { bmp.close(); } catch (_) { }
        }
        return c;
    }
    function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }

    // la = the parsed localStorage checkpoint (schema >= 3). Reads + decodes everything up front so apply() is synchronous.
    async function prepare(la) {
        var recs = (la && la.layers) || [], err = null, all = [];
        try { all = await readAll(); } catch (e) { err = e; }
        var byId = {};
        var maskById = {}, adjById = {};
        all.forEach(function (r) {
            if (!r || typeof r.key !== 'string' || r.sessionId !== la.sessionId) return;
            if (r.key.indexOf('layer:') === 0) byId[r.id] = r;
            else if (r.key.indexOf('mask:') === 0 && r.pcMask) maskById[r.id] = r;
            else if (r.key.indexOf('adj:') === 0 && r.pcAdj) adjById[r.id] = r;
        });
        var decoded = {};
        for (var i = 0; i < recs.length; i++) {
            var r = recs[i]; if (!(r.added || r.px) || !byId[r.id]) continue;
            try { decoded[r.id] = await decode(byId[r.id]); } catch (_) { }
        }
        var nAdded = recs.filter(function (r) { return r.added; }).length;
        var nText = recs.filter(function (r) { return r.added && r.txt; }).length;
        var nPaint = recs.filter(function (r) { return !r.added && r.px; }).length;
        var nMissing = recs.filter(function (r) { return (r.added || r.px) && !decoded[r.id]; }).length;
        var nMask = (window.SPB_TLAY_OFF || !window.SPBPcLayerMask) ? 0 : recs.filter(function (r) { return r.msk && maskById[r.id]; }).length;
        var nAdj = (window.SPB_TLAY_OFF || !window.SPBPcAdjust) ? 0 : recs.filter(function (r) { return r.adj && adjById[r.id]; }).length;
        var nAdjAdded = (window.SPB_TLAY_OFF || !window.SPBPcAdjust) ? 0 : recs.filter(function (r) { return r.added && r.adj && adjById[r.id]; }).length;
        var px = null;   // [SPB-PERSIST-ALL 2026-10-10 lane PERSIST-ALL; matrix crash: 5 of 14 tools lost -> 0] layer materials / Number Kit / Sponsor Kit ride in the persist registry's own IndexedDB rows (kill switch SPB_PERSIST_ALL_OFF)
        try { if (window.SPB_PERSIST && typeof window.SPB_PERSIST.prepareRecovery === 'function') px = await window.SPB_PERSIST.prepareRecovery(la); } catch (_px) { px = null; }
        var parts = [];
        // [SPB-TFX3 2026-10-10 lane TOOLS-FIX-3] an adjustment layer has no pixels of its own: it is counted on its own line ("with its settings"), not as an added layer with pixels
        if (nAdded - nAdjAdded > 0) parts.push(plural(nAdded - nAdjAdded, 'added layer') + (nText ? ' (' + plural(nText, 'live text layer') + ')' : ''));
        if (nPaint) parts.push(plural(nPaint, 'painted layer'));
        var isFlat = String((la && la.sourceFingerprint) || '').indexOf('flat:') === 0;   // [SPB-TFX4 item 4] flat image session
        var msg = 'SPB found your work from an interrupted session for this exact ' + (isFlat ? 'image' : 'source') + '.\n\n' +
            (parts.length ? parts.join(' and ') + ' come back with their pixels, along with your layer order, visibility and opacity.' : 'Your layer order, visibility and opacity come back.') +
            (nAdj ? ' ' + plural(nAdj, 'adjustment layer') + (nAdj === 1 ? ' also comes back with its settings.' : ' also come back with their settings.') : '') +
            (nMask ? ' ' + plural(nMask, 'layer mask') + (nMask === 1 ? ' also comes' : ' also come') + ' back.' : '') +
            (px && px.line ? ' ' + px.line : '') +   // [SPB-PERSIST-ALL 2026-10-10 lane PERSIST-ALL]
            (nMissing ? '\n\n' + plural(nMissing, 'layer') + ' had not been saved yet and will come back empty.' : '') +
            '\n\nRestore them?';
        return {
            message: msg, nAdded: nAdded, nText: nText, nPaint: nPaint, nMissing: nMissing, error: err,
            nMask: nMask, nAdj: nAdj,
            apply: function () {
                var res = applyRecovery(la, byId, decoded, maskById, adjById);
                if (px && res && res.n) { try { res.persist = px.apply(); } catch (_pa) { } }   // [SPB-PERSIST-ALL 2026-10-10 lane PERSIST-ALL] same undo step as the layers
                return res;
            }
        };
    }

    function applyProps(layer, rec) {
        layer.visible = rec.visible !== false;
        layer.opacity = (rec.opacity != null ? rec.opacity : 255);
        layer.blendMode = rec.blendMode || 'source-over';
        layer.locked = !!rec.locked; layer.alphaLock = !!rec.alphaLock; layer.clippingMask = !!rec.clippingMask;
        layer.effects = rec.effects ? JSON.parse(JSON.stringify(rec.effects)) : null;
        layer.adjHue = Number(rec.adjHue) || 0; layer.adjSat = Number(rec.adjSat) || 0; layer.adjBri = Number(rec.adjBri) || 0;
    }
    function applyRecovery(la, byId, decoded, maskById, adjById) {
        var cur = stack(), used = {}, ordered = [], occupied = {}, n = 0, added = 0, painted = 0, text = 0, empty = 0, masks = 0, adjs = 0;
        cur.forEach(function (l) { occupied[String(l.id)] = 1; });
        var matchFor = function (rec) {
            var hit = cur.find(function (l) { return !used[l.id] && rec.path && l.path === rec.path; });
            if (!hit) hit = cur.find(function (l) { return !used[l.id] && l.name === rec.name && (l.groupName || '') === (rec.groupName || ''); });
            if (!hit) hit = cur.find(function (l) { return !used[l.id] && l.name === rec.name; });
            if (hit) used[hit.id] = true;
            return hit || null;
        };
        (la.layers || []).forEach(function (rec) {
            var layer, canvas = decoded[rec.id] || null, pr = byId[rec.id] || null;
            if (rec.added) {
                var bbox = pr ? pr.bbox : (Array.isArray(rec.bbox) ? rec.bbox : null);
                var w = canvas ? canvas.width : (rec.imgW || (bbox ? bbox[2] - bbox[0] : 0)), h = canvas ? canvas.height : (rec.imgH || (bbox ? bbox[3] - bbox[1] : 0));
                if (!w || !h || !bbox) return;
                if (!canvas) { canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h; empty++; }
                var id = String(rec.id); if (occupied[id]) { var k = 2; while (occupied[id + '_r' + k]) k++; id = id + '_r' + k; }
                occupied[id] = 1;
                layer = { id: id, name: rec.name || 'Layer', path: rec.path || '', img: canvas, bbox: bbox.slice(0, 4), groupName: rec.groupName || '' };
                ['groupChain', 'parentGroupKey', 'rasterKey', 'pathParts', 'importVisible', 'ownVisible', 'elementLinkGroups', 'elementInstances'].forEach(function (k2) {
                    if (rec[k2] !== undefined) layer[k2] = jclone(rec[k2]);
                });
                applyProps(layer, rec);
                if (pr && pr.textData && window.SPBTextEdit && typeof window.SPBTextEdit.attach === 'function') { if (window.SPBTextEdit.attach(layer, pr.textData)) text++; }
                added++;
            } else {
                layer = matchFor(rec);
                if (!layer) return;
                applyProps(layer, rec);
                if (rec.px && canvas && pr) {
                    layer.img = canvas; layer.bbox = pr.bbox.slice(0, 4); painted++;
                    if (pr.textData && window.SPBTextEdit && typeof window.SPBTextEdit.attach === 'function') window.SPBTextEdit.attach(layer, pr.textData);
                } else if (Array.isArray(rec.bbox) && layer.img && (layer.img.width === rec.imgW && layer.img.height === rec.imgH)) {
                    layer.bbox = rec.bbox.slice(0, 4);   // same art, only moved (dims match) - same rule as the settings-only restore
                }
            }
            try {   // adjustment layer settings first (sync), then the mask (async, recomposites itself when it lands)
                var arec = adjById && adjById[rec.id];
                if (arec && layer && !layer.pcAdj && !window.SPB_TLAY_OFF && window.SPBPcAdjust && typeof window.SPBPcAdjust.deserialize === 'function') {
                    if (window.SPBPcAdjust.deserialize(layer, arec.pcAdj)) adjs++;
                }
            } catch (_a) { }
            try {
                var mrec = maskById && maskById[rec.id];
                if (mrec && layer && !layer.pcMask && !window.SPB_TLAY_OFF && window.SPBPcLayerMask && typeof window.SPBPcLayerMask.deserialize === 'function') {
                    window.SPBPcLayerMask.deserialize(layer, mrec.pcMask, function () { try { if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); } catch (_e) { } });
                    masks++;
                }
            } catch (_m) { }
            ordered.push(layer); n++;
        });
        var dropped = cur.filter(function (l) { return !used[l.id]; }).length;   // source layers the painter had deleted before the crash
        if (!n) return { n: 0, added: 0, painted: 0, text: 0, empty: 0, dropped: 0 };
        cur.length = 0; Array.prototype.push.apply(cur, ordered);
        try { if (typeof window._publishPSDDocumentState === 'function') window._publishPSDDocumentState(); } catch (_) { }
        return { n: n, added: added, painted: painted, text: text, empty: empty, dropped: dropped, masks: masks, adjustments: adjs };
    }

    // ------------------------------------------------------------------ [SPB-TFX4 2026-10-10 item 4 lane TOOLS-FIX-4] flat (TGA / PNG / JPEG) sources
    // BEFORE (measured, fix4/recovery_flat_before.json): a flat source + added layers + real crash -> reload + same file: the layers were gone and NO prompt came
    // (the prompt lives only in the layered-import path; the checkpoint fingerprint was the live-stack hash; the previous PSD's recovery identity even stayed
    // armed after the flat file replaced it). AFTER: clearPSDDocumentState (every flat load) calls flatSourceLoaded(); a pending crash checkpoint for THIS file is
    // offered once (same single confirm, Ctrl+Z undoes it). Kill switch SPB_TFX4_OFF (window or localStorage) = the old behaviour byte for byte.
    function normPath(v) { return String(v || '').replace(/\\/g, '/').toLowerCase(); }
    function flatLive() { try { var f = window._spbFlatPaintLiveSource; return (f && f.name) ? f : null; } catch (_) { return null; } }
    function flatSourceFile() {          // identity string saved with the checkpoint ('' when not a flat session)
        if (!flatMode || off() || off4()) return '';
        var lf = flatLive();
        return lf ? 'file:' + lf.name : srcFile();
    }
    function flatFp() {                  // 'flat:<w>x<h>:<content fingerprint of the loaded file | name|size|mtime of the picked file>'
        var w = 0, h = 0, part = '';
        try { var c = document.getElementById('paintCanvas'); if (c) { w = c.width | 0; h = c.height | 0; } } catch (_) { }
        var lf = flatLive();
        if (lf) part = [lf.name, lf.size || 0, lf.lastModified || 0].join('|');
        else { try { part = (typeof _spbCommittedSourceFingerprint === 'string') ? _spbCommittedSourceFingerprint : ''; } catch (_) { } }
        return 'flat:' + w + 'x' + h + ':' + part;
    }
    function flatSourceLoaded() {
        if (off() || off4()) return;
        reset();                          // the previous layered document's identity must not stay armed over the flat file
        srcImg = new Map(); persisted = {}; st.active = true; flatMode = true;
        pendingRecovery = true;           // hold the autosave writers: the fresh (empty) flat session must not overwrite the crash checkpoint before the offer is settled
        flatTimer = setTimeout(function () {
            flatTimer = 0;
            offerFlat().catch(function (e) { st.error = String(e && e.message || e); }).then(function () { pendingRecovery = false; schedule('flat-recovery-done'); });
        }, 300);                          // identity (picked-file meta / committed path) is complete a tick after the loader's own clear
    }
    async function offerFlat() {
        if (!flatMode || off() || off4()) return false;
        try { if (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded) return false; } catch (_) { }
        if (stack().length) return false;
        try { if (typeof paintImageData === 'undefined' || !paintImageData) return false; } catch (_) { return false; }
        var key = (typeof SPB_LAYER_AUTOSAVE_KEY !== 'undefined') ? SPB_LAYER_AUTOSAVE_KEY : 'shokker_layer_autosave';
        var raw = null; try { raw = localStorage.getItem(key); } catch (_) { }
        if (!raw) return false;
        var la = null; try { la = JSON.parse(raw); } catch (_) { return false; }
        if (!la || String(la.sourceFingerprint || '').indexOf('flat:') !== 0 || la.cleanClose !== false || !Array.isArray(la.layers) || !la.layers.length || Number(la.schemaVersion) < 3) return false;
        var file = flatSourceFile();
        if (!file || normPath(la.sourcePaintFile) !== normPath(file)) return false;
        if (!((Date.now() - (la.savedAt || 0)) < 7 * 24 * 3600 * 1000)) return false;
        var fp = flatFp();
        if (la.sourceFingerprint !== fp) { toast('Interrupted layers were not restored because this image has changed since they were saved. The current document was left unchanged.', 'warn'); return false; }
        var prep = await prepare(la);
        // the painter may have moved on while the pixels were decoded
        try { if (!flatMode || flatSourceFile() !== file || flatFp() !== fp || stack().length || (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded)) return false; } catch (_) { return false; }
        // [SPB-CONFIRM-POLISH 2026-10-10] native confirm() -> in-app SpbDialog.ask (kill switch SPB_CONFIRM_POLISH_OFF).
        var yes = await SpbDialog.ask('Restore Your Interrupted Session?', { message: String(prep.message).replace(/\s*Restore them\?\s*/, '\n\n').trim(), okLabel: 'Restore Session', cancelLabel: 'Start Fresh', nativeText: prep.message });
        // the painter may have moved on while the box was open: same guard as above
        try { if (!flatMode || flatSourceFile() !== file || flatFp() !== fp || stack().length || (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded)) return false; } catch (_) { return false; }
        if (!yes) { la.cleanClose = true; la.declinedAt = Date.now(); try { localStorage.setItem(key, JSON.stringify(la)); } catch (_) { } return false; }
        try { if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('restore interrupted layer session'); } catch (_) { }
        try { _psdLayersLoaded = true; } catch (_) { }
        var res = prep.apply();
        if (!res || !res.n) { try { _psdLayersLoaded = false; } catch (_) { } return false; }
        var top = stack()[stack().length - 1];
        try { if (top && typeof selectPSDLayer === 'function') selectPSDLayer(top.id); } catch (_) { }
        try { if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); } catch (_) { }
        try { if (typeof renderLayerPanel === 'function') renderLayerPanel(); } catch (_) { }
        try { localStorage.removeItem(key); } catch (_) { }
        try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); } catch (_) { }
        toast('Restored your interrupted session: ' + plural(res.n, 'layer') + (res.text ? ', ' + res.text + ' live text' : '') + '. Ctrl+Z undoes this.');
        try { window.__spbTfx4FlatRecovery = { n: res.n, text: res.text, empty: res.empty, at: Date.now() }; } catch (_) { }
        return true;
    }

    // [SPB-TFX3 2026-10-09 TEXT-BUTTON] kill switch for the new Text toolbar button (markup is always present; hidden when the lane is switched off)
    try { if (off()) { var _tb = document.getElementById('vtModeText'); if (_tb) _tb.style.display = 'none'; } } catch (_e) { }

    // [SPB-TFX3 2026-10-09 AUDIT2-F8 lane TOOLS-FIX-3] a live text layer (img.__spbText) turns into plain pixels the moment ANY pixel operation (brush, eraser, fill,
    // gradient, flip...) replaces its canvas - by design (js/canvas/pc-text-edit.js), and Ctrl+Z brings it back - but nothing told the painter: the text just stopped being
    // editable (Text tool click on it opened an EMPTY box). Now one quiet toast says so. The two explicit rasterize paths set window.__tfx3RastAt and keep their own toasts.
    var liveText = {};
    function watchLiveText() {
        if (off() || document.hidden) return;
        var L = stack(), seen = {}, ft = false;
        try { ft = typeof freeTransformState !== 'undefined' && !!freeTransformState; } catch (_) { }
        for (var i = 0; i < L.length; i++) {
            var l = L[i]; if (!l || l.id == null) continue;
            var id = String(l.id); seen[id] = 1;
            if (l.img && l.img.__spbText) { liveText[id] = l.name || 'Text'; continue; }
            if (liveText[id] === undefined) continue;
            var nm = liveText[id]; delete liveText[id];
            if (!ft && Date.now() - (window.__tfx3RastAt || 0) > 4000) toast('"' + nm + '" is now plain pixels, so it can no longer be edited as text - Ctrl+Z brings the live text back', 'info');
        }
        for (var k in liveText) if (!seen[k]) delete liveText[k];
    }
    try { setInterval(watchLiveText, 700); } catch (_) { }

    window.SPBTfx3Recovery = {
        markSource: markSource, reset: reset, active: active, fingerprint: function () { return (flatMode && !off() && !off4()) ? flatFp() : srcFp; }, sourceOnly: sourceOnly, decorate: decorate, schedule: schedule, flush: flush,
        flatSourceLoaded: flatSourceLoaded, flatSourceFile: flatSourceFile, flat: function () { return flatMode && !off() && !off4(); }, offerFlat: offerFlat,   // [SPB-TFX4 item 4]
        setPending: setPending, pending: function () { return pendingRecovery; }, prepare: prepare,
        status: function () { return Object.assign({}, st); }, isSource: isSource, isModifiedSource: isModifiedSource
    };
})();
