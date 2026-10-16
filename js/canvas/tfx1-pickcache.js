/* [SPB-TFX1 2026-10-09 TA-027] Pick Item / Move hover preview cache.
 *
 * Problem (audit TA-027, real owner car): hovering with PICK ITEM (and MOVE with a content layer selected) ran, on EVERY ~11 fps hover tick,
 *   (a) a full-layer getImageData for every layer the pointer could hit (getTopmostVisibleLayerAtCanvasPoint -> isPointOnLayerOpaque), and
 *   (b) a JS flood fill over a 2048x2048 alpha map (selectConnectedLayerPixelsAtPoint previewOnly) that visits ~1M px on a big base layer
 *   = 0.6-1.2 s per hover tick: the app froze while the painter aimed.
 *
 * Now: one alpha plane per layer (Uint8) + one 8-connected component label map per (layer, alpha threshold) with per-component
 * count / canvas-bounds bbox are built ONCE and reused, so a hover is an O(1) lookup. Results are byte-identical to the flood fill
 * (same threshold, same 8-connectivity, same in-canvas bbox, same +-40 px auto-grow rule) - see tfx1 test drive_pickcache.py.
 *
 * Cache validity: a generation counter is bumped by invalidateLayerVisibleContributionCache(), recompositeFromLayers(), any pointerdown
 * outside the canvas, Ctrl/Cmd/Delete/Backspace/Enter keydowns (undo/redo/commit) and entering a hover tool; entries are also keyed on
 * the layer's img object, size and bbox. Click-picks (non-preview) never use this cache - they keep reading fresh pixels.
 * Kill switch: window.SPB_TFX1_OFF = true (or localStorage SPB_TFX1_OFF='1') -> callers fall back to the original code.
 */
(function () {
    'use strict';
    var MAX_BYTES = 280 * 1024 * 1024;   // alpha planes (4 MB each at 2048^2) + label maps (16 MB each, lazily); LRU-evicted past this budget
    var cache = new Map();               // layer.id -> entry (Map keeps insertion order = LRU)
    var gen = 1;
    var scratch = null, scratchCtx = null;

    function off() { return window.SPB_TFX1_OFF === true; }
    function bump() { gen++; }

    function entryBytes(e) {
        var b = e.a.length;
        for (var k in e.labels) { var L = e.labels[k]; b += L.lab.byteLength + L.parent.byteLength + L.count.byteLength * 5; }
        return b;
    }
    function trim(keepId) {
        var total = 0; cache.forEach(function (e) { total += entryBytes(e); });
        var it = cache.keys();
        while (total > MAX_BYTES && cache.size > 1) {
            var k = it.next().value;
            if (k === undefined) break;
            if (k === keepId) continue;
            total -= entryBytes(cache.get(k)); cache.delete(k);
        }
    }

    function dims(img) {
        return { w: (img && (img.width || img.naturalWidth)) || 0, h: (img && (img.height || img.naturalHeight)) || 0 };
    }

    function entryFor(layer) {
        if (!layer || !layer.img) return null;
        var d = dims(layer.img);
        if (!d.w || !d.h) return null;
        var bb = Array.isArray(layer.bbox) ? layer.bbox : [0, 0, d.w, d.h];
        var ox = bb[0] || 0, oy = bb[1] || 0;
        var e = cache.get(layer.id);
        if (e && e.gen === gen && e.img === layer.img && e.w === d.w && e.h === d.h && e.ox === ox && e.oy === oy) {
            cache.delete(layer.id); cache.set(layer.id, e);        // LRU touch
            return e;
        }
        // (re)build the alpha plane
        var t0 = performance.now();
        if (!scratch) { scratch = document.createElement('canvas'); }
        if (scratch.width !== d.w || scratch.height !== d.h) { scratch.width = d.w; scratch.height = d.h; scratchCtx = null; }
        if (!scratchCtx) scratchCtx = scratch.getContext('2d', { willReadFrequently: true });
        scratchCtx.clearRect(0, 0, d.w, d.h);
        scratchCtx.drawImage(layer.img, 0, 0, d.w, d.h);
        var px = scratchCtx.getImageData(0, 0, d.w, d.h).data;
        var n = d.w * d.h, a = new Uint8Array(n);
        for (var i = 0, j = 3; i < n; i++, j += 4) a[i] = px[j];
        e = { id: layer.id, gen: gen, img: layer.img, w: d.w, h: d.h, ox: ox, oy: oy, a: a, labels: {}, buildMs: performance.now() - t0 };
        cache.delete(layer.id); cache.set(layer.id, e);
        trim(e.id);
        return e;
    }

    // 8-connected component labelling of (alpha > thr). Stats are over pixels whose CANVAS position is inside [0,cw)x[0,ch)
    // (exactly the pixels the original flood fill counted); labels themselves cover the whole layer plane (the flood walked through
    // off-canvas pixels too, so connectivity is identical).
    function buildLabels(e, thr, cw, ch) {
        var t0 = performance.now();
        var w = e.w, h = e.h, a = e.a, n = w * h;
        var lab = new Int32Array(n);
        var cap = (((w + 1) >> 1) * ((h + 1) >> 1)) + 2;
        var parent = new Int32Array(cap);
        var next = 0;
        function find(x) { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
        for (var y = 0; y < h; y++) {
            var row = y * w;
            for (var x = 0; x < w; x++) {
                var i = row + x;
                if (a[i] <= thr) continue;
                var l = 0, nb;
                if (x > 0 && (nb = lab[i - 1])) l = nb;
                if (y > 0) {
                    if (x > 0 && (nb = lab[i - w - 1])) {
                        if (!l) l = nb; else if (nb !== l) { var r1 = find(l), r2 = find(nb); if (r1 < r2) { parent[r2] = r1; l = r1; } else { parent[r1] = r2; l = r2; } }
                    }
                    if ((nb = lab[i - w])) {
                        if (!l) l = nb; else if (nb !== l) { var r3 = find(l), r4 = find(nb); if (r3 < r4) { parent[r4] = r3; l = r3; } else { parent[r3] = r4; l = r4; } }
                    }
                    if (x < w - 1 && (nb = lab[i - w + 1])) {
                        if (!l) l = nb; else if (nb !== l) { var r5 = find(l), r6 = find(nb); if (r5 < r6) { parent[r6] = r5; l = r5; } else { parent[r5] = r6; l = r6; } }
                    }
                }
                if (!l) { l = ++next; parent[l] = l; }
                lab[i] = l;
            }
        }
        for (var k = 1; k <= next; k++) parent[k] = find(k);
        parent = parent.slice(0, next + 1);                   // flat root table only (the provisional-label capacity is up to w*h/4)
        var count = new Int32Array(next + 1), minX = new Int32Array(next + 1).fill(2147483647), minY = new Int32Array(next + 1).fill(2147483647);
        var maxX = new Int32Array(next + 1).fill(-1), maxY = new Int32Array(next + 1).fill(-1);
        var ox = e.ox, oy = e.oy;
        for (var yy = 0; yy < h; yy++) {
            var cy = oy + yy;
            if (cy < 0 || cy >= ch) continue;
            var rw = yy * w;
            var xs = Math.max(0, -ox), xe = Math.min(w, cw - ox);
            for (var xx = xs; xx < xe; xx++) {
                var l2 = lab[rw + xx];
                if (!l2) continue;
                var r = parent[l2], cx = ox + xx;
                count[r]++;
                if (cx < minX[r]) minX[r] = cx;
                if (cx > maxX[r]) maxX[r] = cx;
                if (cy < minY[r]) minY[r] = cy;
                if (cy > maxY[r]) maxY[r] = cy;
            }
        }
        var L = { thr: thr, cw: cw, ch: ch, lab: lab, parent: parent, count: count, minX: minX, minY: minY, maxX: maxX, maxY: maxY, ms: performance.now() - t0, comps: next };
        e.labels[thr] = L;
        trim(e.id);
        return L;
    }

    function labelsFor(e, thr, cw, ch) {
        var L = e.labels[thr];
        if (L && L.cw === cw && L.ch === ch) return L;
        return buildLabels(e, thr, cw, ch);
    }

    // true when canvas point (px,py) is on an opaque (alpha > thr) pixel of the layer; null when the cache cannot answer
    function opaqueAt(layer, px, py, thr) {
        var e = entryFor(layer);
        if (!e) return null;
        var lx = px - e.ox, ly = py - e.oy;
        if (lx < 0 || ly < 0 || lx >= e.w || ly >= e.h) return false;
        return e.a[ly * e.w + lx] > (thr == null ? 10 : thr);
    }

    // The previewOnly branch of selectConnectedLayerPixelsAtPoint, answered from the cache.
    //   returns null  -> cache cannot answer (caller runs the original code)
    //   {oob:true}    -> the seed lies outside the layer plane (original returned false)
    //   {miss:true}   -> no opaque pixel at / near the seed (original toasted and returned false)
    //   {count, x1,y1,x2,y2} -> connected element stats (count 0 = nothing inside the canvas)
    function preview(layer, canvasX, canvasY, o) {
        if (off()) return null;
        var e = entryFor(layer);
        if (!e) return null;
        var thr = (o.textMode ? 4 : 10);
        var lx0 = canvasX - e.ox, ly0 = canvasY - e.oy;
        var lw = e.w, lh = e.h, a = e.a;
        if (lx0 < 0 || ly0 < 0 || lx0 >= lw || ly0 >= lh) return { oob: true };
        if (a[ly0 * lw + lx0] <= thr) {
            var snapped = false;
            if (o.allowSnap) {
                var ds = (typeof o.dispScale === 'function') ? o.dispScale() : 0.23;
                var R = Math.max(22, Math.round(26 / Math.max(0.05, ds)));
                for (var r = 1; r <= R && !snapped; r++) {
                    for (var dy = -r; dy <= r && !snapped; dy++) {
                        for (var dx = -r; dx <= r && !snapped; dx += (Math.abs(dy) === r ? 1 : 2 * r)) {
                            var nx = lx0 + dx, ny = ly0 + dy;
                            if (nx < 0 || ny < 0 || nx >= lw || ny >= lh) continue;
                            if (a[ny * lw + nx] > thr) { lx0 = nx; ly0 = ny; snapped = true; }
                        }
                    }
                }
            }
            if (!snapped) return { miss: true };
        }
        var L = labelsFor(e, thr, o.pcW, o.pcH);
        var root = L.parent[L.lab[ly0 * lw + lx0]];
        var count = L.count[root];
        if (!(count > 0)) return { count: 0 };
        var minCx = L.minX[root], minCy = L.minY[root], maxCx = L.maxX[root], maxCy = L.maxY[root];
        if (count > 0 && minCx < 2147483647) {
            var iw = maxCx - minCx, ih = maxCy - minCy;
            if (iw < 250 && ih < 250) {               // same +-40 px "whole logo" growth as the original
                var grow = 40;
                var sx1 = Math.max(0, Math.floor(minCx - grow - e.ox)), sy1 = Math.max(0, Math.floor(minCy - grow - e.oy));
                var sx2 = Math.min(lw, Math.ceil(maxCx + grow - e.ox) + 1), sy2 = Math.min(lh, Math.ceil(maxCy + grow - e.oy) + 1);
                for (var yy = sy1; yy < sy2; yy++) {
                    var rowp = yy * lw;
                    for (var xx = sx1; xx < sx2; xx++) {
                        if (a[rowp + xx] > thr) {
                            var cx = e.ox + xx, cy = e.oy + yy;
                            if (cx < minCx) minCx = cx; if (cy < minCy) minCy = cy;
                            if (cx > maxCx) maxCx = cx; if (cy > maxCy) maxCy = cy;
                        }
                    }
                }
            }
        }
        return { count: count, x1: Math.floor(minCx), y1: Math.floor(minCy), x2: Math.ceil(maxCx + 1), y2: Math.ceil(maxCy + 1) };
    }

    // Warm the caches in short idle slices so the first hover after switching to a pick tool is already O(1).
    var warmTimer = null;
    function warm() {
        if (off()) return;
        if (warmTimer) clearTimeout(warmTimer);
        var layers = (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers.slice().reverse() : [];
        var pc = document.getElementById('paintCanvas');
        var cw = pc ? pc.width : 2048, ch = pc ? pc.height : 2048;
        var queue = [];
        layers.forEach(function (l) { if (l && l.img && l.visible !== false && (l.opacity == null || l.opacity > 0)) queue.push(l); });
        function step() {
            warmTimer = null;
            if (off()) return;
            var l = queue.shift();
            if (!l) return;
            try { var e = entryFor(l); if (e) labelsFor(e, 10, cw, ch); } catch (_e) { }
            warmTimer = setTimeout(step, 16);
        }
        warmTimer = setTimeout(step, 30);
    }

    // generation bumps
    document.addEventListener('pointerdown', function (e) {
        var t = e.target;
        if (t && (t.id === 'paintCanvas' || t.id === 'transformCanvas' || t.id === 'regionCanvas')) return;
        bump();
    }, true);
    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey || e.metaKey || e.key === 'Delete' || e.key === 'Backspace' || e.key === 'Enter') bump();
    }, true);

    window.SPBTfx1Pick = {
        bump: bump, warm: warm, opaqueAt: opaqueAt, preview: preview,
        stats: function () { var o = { gen: gen, entries: [] }; cache.forEach(function (e) { o.entries.push({ id: e.id, w: e.w, h: e.h, buildMs: Math.round(e.buildMs * 10) / 10, labels: Object.keys(e.labels).map(function (k) { var L = e.labels[k]; return { thr: +k, ms: Math.round(L.ms * 10) / 10, comps: L.comps }; }) }); }); return o; },
        _entryFor: entryFor, _labelsFor: labelsFor
    };
}());
