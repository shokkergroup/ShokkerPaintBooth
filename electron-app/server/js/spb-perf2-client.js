/* [SPB-PERF2 2026-10-10 PERF-2 lane] runtime speed helpers for the main-thread freeze (PERF-2 target 1). ONE kill switch for everything in this file and for every [SPB-PERF2]
 * hunk in the other files: window.SPB_PERF2_OFF === true (or localStorage SPB_PERF2_OFF = '1'; folded into the window flag below).
 *
 * The freeze: with a car loaded the main thread froze 1.0-1.9 s about every 8 s. Chain: js/spb-pbn.js tick (500 ms) -> sig -> env -> js/spb-pro-ai.js editEnv()
 * (re-built when its 2.5-20 s memo expired) -> shownShares -> js/spb-pro-zone-kit.js probeRegion/footprint/ownTest -> getZoneSourceLayersUnionMask, which copies a
 * 4 MB mask on EVERY call (about 100 calls per rebuild = 60 % of the freeze). It delayed every helper reply ("make the hood red" waited 2.5-4.6 s behind it).
 * Two fixes live here, the rest are small commented hunks in spb-pro-ai.js / spb-pro-zone-kit.js:
 *   1. unionRO()       - the layer-union mask WITHOUT the copy, for callers that only READ it (zone-kit). Same maths as the original (it is the original loop), same
 *                        merge for multi-layer zones, cached on the identity of the per-layer masks (exactly the key perf1's union memo uses). Installs only while
 *                        the original function's source still has the fingerprint it was written against; otherwise it just calls the original (copying) function.
 *   2. inputsToken()   - a string that changes whenever ANY input of the helper environment changes: every zone field (typed arrays / canvases by identity), every
 *                        layer (id, name, visibility, opacity, blend, canvas identity), the layer composite revisions, the paint pixels (identity + a stride-8 sample
 *                        hash) and the car map (signature, roles). editEnv() re-validates an expired memo against it instead of rebuilding: same inputs -> same environment,
 *                        so an idle page rebuilds NOTHING (it used to rebuild every 2.5-20 s). When the token cannot be computed it returns null and editEnv() keeps the old rule.
 * Audit and numbers: _easy_claude_work/perf2/PROGRESS.md.
 */
(function () {
    'use strict';
    var W = window;
    try { if (W.localStorage && W.localStorage.getItem('SPB_PERF2_OFF') === '1') W.SPB_PERF2_OFF = true; } catch (e0) {}
    if (W.__spbPerf2) return;
    var P = W.__spbPerf2 = { version: '2026-10-10-p2a', stats: { roCalls: 0, roMerged: 0, roMergeHits: 0, tokens: 0, tokenMs: 0, tokenNull: 0 } };
    function off() { return W.SPB_PERF2_OFF === true; }
    P.off = off;

    // ------------------------------------------------------------------ 1. read-only layer union
    var FP = 'dbbfe9c7', FP_LEN = 773, roOK = null, cache = [], MAXE = 4;          // the same source fingerprint perf1's union memo was written against
    function fingerprint(fn) {
        var n = Function.prototype.toString.call(fn).replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, '');
        var h = 0x811c9dc5;
        for (var i = 0; i < n.length; i++) { h ^= n.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
        return { h: h.toString(16), n: n.length };
    }
    function origUnion() { var f = W.getZoneSourceLayersUnionMask; return f && f.__orig ? f.__orig : f; }
    function roReady() {
        if (roOK !== null) return roOK;
        var f = origUnion();
        if (typeof f !== 'function' || typeof W.getLayerVisibleContributionMask !== 'function' || typeof _psdLayers === 'undefined') return false;          // not loaded yet: ask again next call
        var fp = fingerprint(f); roOK = (fp.h === FP && fp.n === FP_LEN);
        P.stats.roWhy = roOK ? 'ok' : 'source changed (' + fp.h + '/' + fp.n + ')';
        return roOK;
    }
    function rev() { try { return typeof _layerCompositeRevision !== 'undefined' ? _layerCompositeRevision : -1; } catch (e) { return -1; } }
    /* Same result shape as getZoneSourceLayersUnionMask(zone, w, h, excludeLayerId), but `union` is SHARED: the caller must only read it. */
    P.unionRO = function (zone, w, h, excludeLayerId) {
        var orig = W.getZoneSourceLayersUnionMask;
        if (off() || !roReady()) return orig.apply(W, arguments);
        P.stats.roCalls++;
        var ids = (typeof W.zoneSourceLayerIds === 'function') ? W.zoneSourceLayerIds(zone) : (zone && zone.sourceLayer ? [zone.sourceLayer] : []);
        var masks = [], found = 0, hiddenCount = 0, i, j;
        for (i = 0; i < ids.length; i++) {          // the original loop, verbatim semantics
            var id = ids[i];
            var l = _psdLayers.find(function (x) { return x && x.id === id; });
            if (!l || !l.img) continue;
            if (l.visible === false) { hiddenCount++; continue; }
            var m = W.getLayerVisibleContributionMask(l, w, h, excludeLayerId);
            if (!m) continue;
            found++;
            masks.push(m);
        }
        var union = null;
        if (masks.length === 1) union = masks[0];
        else if (masks.length > 1) {
            var r = rev(), hit = null;
            for (j = cache.length - 1; j >= 0; j--) {
                var e = cache[j];
                if (e.rev !== r) { cache.splice(j, 1); continue; }
                if (!hit && e.masks.length === masks.length) {
                    var same = true;
                    for (i = 0; i < masks.length; i++) if (e.masks[i] !== masks[i]) { same = false; break; }
                    if (same) hit = e;
                }
            }
            if (hit) { P.stats.roMergeHits++; union = hit.union; }
            else {
                P.stats.roMerged++;
                var u = new Uint8Array(masks[0]);
                for (i = 1; i < masks.length; i++) { var mm = masks[i]; for (j = 0; j < u.length; j++) { if (mm[j] > u[j]) u[j] = mm[j]; } }
                cache.push({ rev: r, masks: masks, union: u });
                if (cache.length > MAXE) cache.shift();
                union = u;
            }
        }
        return { union: union, found: found, hiddenCount: hiddenCount, requested: ids.length, firstLayer: ids.length ? _psdLayers.find(function (x) { return x && x.id === ids[0]; }) : null, ids: ids };
    };

    // ------------------------------------------------------------------ 2. inputs token for the helper environment
    var objIds = (typeof WeakMap === 'function') ? new WeakMap() : null, objSeq = 0;
    function rep(k, v) {
        if (v && typeof v === 'object') {
            if (ArrayBuffer.isView(v) || v instanceof ArrayBuffer || (typeof ImageData !== 'undefined' && v instanceof ImageData) || (typeof Node !== 'undefined' && v instanceof Node) || (typeof ImageBitmap !== 'undefined' && v instanceof ImageBitmap)) {
                if (!objIds.has(v)) objIds.set(v, ++objSeq);
                return '#' + objIds.get(v) + (v.length != null ? ':' + v.length : '');
            }
        } else if (typeof v === 'function') return undefined;
        return v;
    }
    function idOf(o) { if (!o) return 0; if (!objIds.has(o)) objIds.set(o, ++objSeq); return objIds.get(o); }
    function paintTok() {
        var pd = null; try { pd = (typeof paintImageData !== 'undefined') ? paintImageData : null; } catch (e) { pd = null; }
        if (!pd || !pd.data) return 'nopaint';
        var w = pd.width, h = pd.height, d = pd.data, hs = 0x811c9dc5, x, y, o;
        for (y = 0; y < h; y += 4) for (x = 0; x < w; x += 4) { /* stride 4 = every pixel the probes sample (probeRegion scans stride 4 / 16, paintColours / footprint stride 16) */ o = (y * w + x) * 4; hs = Math.imul(hs ^ (d[o] | (d[o + 1] << 8) | (d[o + 2] << 16) | (d[o + 3] << 24)), 0x01000193); }
        return idOf(pd) + ':' + w + 'x' + h + ':' + (hs >>> 0).toString(36);
    }
    function carTok() {
        var C = W.SpbProCar; if (!C) return 'nocar';
        var s = '';
        try { s += (C.signature ? C.signature() : '') + '|' + (C.hasIslands ? C.hasIslands() : '') + '|' + (C.layoutSig ? C.layoutSig() : ''); } catch (e1) { s += 'x'; }
        try { s += '|' + JSON.stringify(C.roles ? C.roles() : null); } catch (e2) { s += '|y'; }
        try { var rc = C.recognized ? C.recognized() : null; s += '|' + (rc ? (rc.id || rc.name || rc.key || JSON.stringify(rc).slice(0, 80)) : ''); } catch (e3) {}
        return s;
    }
    P.inputsToken = function () {
        if (off() || !objIds) return null;
        var t0 = performance.now();
        try {
            var z = JSON.stringify(typeof zones !== 'undefined' ? zones : null, rep);
            var l = JSON.stringify(typeof _psdLayers !== 'undefined' ? _psdLayers : null, rep);
            var tok = z + '\u0001' + l + '\u0001' + rev() + ':' + (W._spbLayerRev || 0) + '\u0001' + paintTok() + '\u0001' + carTok();
            P.stats.tokens++; P.stats.tokenMs += performance.now() - t0;
            return tok;
        } catch (e) { P.stats.tokenNull++; return null; }
    };
})();
