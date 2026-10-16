/* Non-destructive layer masks for the SPB layer stack (ticket TL-15, TOOLS-LAYERS lane, 2026-10-09).
 * Semantics follow PhotoCraft (crates/compose/src/masks.rs: effective mask = 1 - density * (1 - m), each blurred by its feather,
 * multiplied into the layer alpha; commands layer.layerMask.revealAll / hideAll / revealSelection / hideSelection / enabled /
 * apply / delete, invert) - (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 (THIRD_PARTY_NOTICES.md).
 * Modified: rewritten in JavaScript for Shokker Paint Booth (Canvas2D, per-layer immutable mask objects, undo through the existing
 * layer history). Owner direction: "tools feel like a feature, not half assed".
 *
 * Model: layer.pcMask = frozen { c: opaque grey canvas (canvas sized), ax, ay: anchor (the layer origin the mask belongs to, so the
 *   mask follows the layer when it moves), b0, b1, img: sync bookkeeping, enabled, density 0..1, feather px, def: 0|255 }.
 *   Mask value of a pixel = luminance of c over black (white = visible, black = hidden). The object is replaced, never mutated,
 *   so stack snapshots (which keep other own properties by reference) restore it exactly.
 * Compositing: _spbCompositeLayerStack is wrapped; masked layers are swapped for proxy layers whose image is the masked image
 *   (effects, clipping bases, ownership composites all see the masked result). Mask painting reuses the existing brush pipeline:
 *   _initLayerPaintCanvas / _commitLayerPaint swap the mask surface in for exactly the length of the init / commit call.
 * Kill switch: window.SPB_TLAY_OFF = true (or localStorage SPB_TLAY_OFF=1): masks stop applying, UI is not injected.
 */
(function () {
    'use strict';
    if (window.SPBPcLayerMask) return;
    var VERSION = 'pcm-1';
    function off() { return window.SPB_TLAY_OFF === true; }
    try { if (window.localStorage && window.localStorage.getItem('SPB_TLAY_OFF') === '1') window.SPB_TLAY_OFF = true; } catch (_e) {}

    var stats = { composites: 0, lastComposeMs: 0, strokes: 0, adds: 0, bakes: 0 };
    var undoers = [];
    var editId = null;          // layer whose mask is being painted
    var savedColors = null;
    var stroke = null;          // { id, real:{img,bbox}, Sw, mOld, zoneclip }  mask stroke in progress
    var swapped = null;         // { id, real:{img,bbox}, mOld }  inside _commitLayerPaint
    var gesture = null;
    var pendingBake = null;     // merge down: bake these layer ids right after the history snapshot

    function toast(msg, kind) { try { if (typeof window.showToast === 'function') window.showToast(msg, kind); } catch (_e) {} }
    function mk(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }
    function cx(c) { return c.getContext('2d', { willReadFrequently: true }); }
    function cdims() { var pc = document.getElementById('paintCanvas'); return { w: pc ? pc.width : 2048, h: pc ? pc.height : 2048 }; }
    function stack() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; }
    function byId(id) { var s = stack(); for (var i = 0; i < s.length; i++) if (s[i] && s[i].id === id) return s[i]; return null; }
    function clamp01(v) { v = Number(v); return v < 0 ? 0 : (v > 1 ? 1 : (isNaN(v) ? 1 : v)); }
    function freeze(o) { return Object.freeze(o); }

    // ------------------------------------------------------------------ grey -> alpha (luminance of the mask over black)
    function ensureFilter() {
        if (document.getElementById('pcm-svg')) return;
        var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        s.setAttribute('id', 'pcm-svg'); s.setAttribute('width', '0'); s.setAttribute('height', '0'); s.setAttribute('aria-hidden', 'true');
        s.style.cssText = 'position:absolute;width:0;height:0;pointer-events:none';
        s.innerHTML = '<filter id="pcm-l2a" color-interpolation-filters="sRGB" x="0" y="0" width="100%" height="100%"><feColorMatrix type="luminanceToAlpha"/></filter>';
        (document.body || document.documentElement).appendChild(s);
    }
    function toAlpha(S, cache) {
        var hit = cache ? alphaCache.get(S) : null;
        if (hit) return hit;
        ensureFilter();
        var w = S.width, h = S.height, src = S;
        if (!S.__pcOpaque) {   // flatten over black so erased / semi-transparent pixels read as hidden
            src = mk(w, h); var f = cx(src); f.fillStyle = '#000'; f.fillRect(0, 0, w, h); f.drawImage(S, 0, 0);
        }
        var A = mk(w, h), a = cx(A);
        a.filter = 'url(#pcm-l2a)'; a.drawImage(src, 0, 0); a.filter = 'none';
        if (cache) alphaCache.set(S, A);
        return A;
    }
    var alphaCache = new WeakMap();   // committed mask surface -> alpha canvas
    function featherAlpha(A, f) {
        var w = A.width, h = A.height, p = Math.min(300, Math.ceil(f * 3) + 2);
        var P = mk(w + 2 * p, h + 2 * p), g = cx(P);
        g.imageSmoothingEnabled = false;
        g.drawImage(A, p, p);
        g.drawImage(A, 0, 0, 1, h, 0, p, p, h); g.drawImage(A, w - 1, 0, 1, h, w + p, p, p, h);
        g.drawImage(A, 0, 0, w, 1, p, 0, w, p); g.drawImage(A, 0, h - 1, w, 1, p, h + p, w, p);
        g.drawImage(A, 0, 0, 1, 1, 0, 0, p, p); g.drawImage(A, w - 1, 0, 1, 1, w + p, 0, p, p);
        g.drawImage(A, 0, h - 1, 1, 1, 0, h + p, p, p); g.drawImage(A, w - 1, h - 1, 1, 1, w + p, h + p, p, p);
        var B = mk(w + 2 * p, h + 2 * p), b = cx(B);
        b.filter = 'blur(' + f + 'px)'; b.drawImage(P, 0, 0); b.filter = 'none';
        var out = mk(w, h), o = cx(out);
        o.drawImage(B, p, p, w, h, 0, 0, w, h);
        return out;
    }
    // effective mask alpha = 1 - density (1 - m), blurred by feather (PhotoCraft masks.rs build_mask); the two operations commute
    function effAlpha(m, A, noFeather) {
        var d = clamp01(m.density == null ? 1 : m.density), f = noFeather ? 0 : Math.max(0, Number(m.feather) || 0);
        if (d >= 0.9999 && f <= 0) return A;
        var key = d.toFixed(4) + '|' + f.toFixed(2);
        A.__pcEff = A.__pcEff || {};
        if (A.__pcEff[key]) return A.__pcEff[key];
        var cur = A;
        if (f > 0) cur = featherAlpha(cur, f);
        if (d < 0.9999) {
            var D = mk(A.width, A.height), g = cx(D);
            g.fillStyle = 'rgba(0,0,0,' + (1 - d) + ')'; g.fillRect(0, 0, D.width, D.height);
            g.globalCompositeOperation = 'lighter'; g.globalAlpha = d; g.drawImage(cur, 0, 0);
            cur = D;
        }
        var keys = Object.keys(A.__pcEff); if (keys.length > 3) delete A.__pcEff[keys[0]];
        A.__pcEff[key] = cur;
        return cur;
    }
    var maskedCache = new WeakMap();   // real layer image -> { A, ax, ay, out }
    function maskedImage(real, A, ax, ay) {
        var hit = maskedCache.get(real);
        if (hit && hit.A === A && hit.ax === ax && hit.ay === ay) return hit.out;
        var w = real.naturalWidth || real.width, h = real.naturalHeight || real.height;
        var out = mk(w, h), g = cx(out);
        g.drawImage(real, 0, 0);
        g.globalCompositeOperation = 'destination-in';
        g.drawImage(A, -ax, -ay);
        maskedCache.set(real, { A: A, ax: ax, ay: ay, out: out });
        return out;
    }

    // ------------------------------------------------------------------ mask bookkeeping (follows the layer when it moves)
    function syncMask(L) {
        var m = L.pcMask; if (!m) return null;
        if ((swapped && swapped.id === L.id) || (stroke && stroke.id === L.id && stroke.initing)) return m;
        var b = L.bbox || [0, 0], b0 = b[0] | 0, b1 = b[1] | 0;
        if (m.img !== L.img || m.b0 !== b0 || m.b1 !== b1) {
            var ax = m.ax, ay = m.ay;
            if (m.img !== L.img) { ax = b0 - (m.b0 - m.ax); ay = b1 - (m.b1 - m.ay); }   // pixels replaced (paint commit crop / undo): stay put
            m = L.pcMask = freeze(Object.assign({}, m, { img: L.img, b0: b0, b1: b1, ax: ax, ay: ay }));
        }
        return m;
    }
    function aligned(L, m) {   // the mask as a canvas-aligned opaque surface at the layer's present position
        var d = cdims(), c = mk(d.w, d.h), g = cx(c);
        var b = L.bbox || [0, 0];
        g.fillStyle = (m.def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, d.w, d.h);
        g.drawImage(m.c, (b[0] | 0) - m.ax, (b[1] | 0) - m.ay);
        c.__pcOpaque = true;
        return c;
    }
    function flatOpaque(img, ox, oy) {   // committed pipeline result (maybe cropped, maybe with erased holes) -> full opaque surface
        var d = cdims(), c = mk(d.w, d.h), g = cx(c);
        g.fillStyle = '#000'; g.fillRect(0, 0, d.w, d.h);
        g.drawImage(img, ox | 0, oy | 0);
        c.__pcOpaque = true;
        return c;
    }
    function newMaskObj(L, S, extra) {
        var b = L.bbox || [0, 0];
        return freeze(Object.assign({ c: S, ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0, img: L.img, enabled: true, density: 1, feather: 0, def: 255 }, extra || {}));
    }
    function touch() {
        window._spbLayerRev = (window._spbLayerRev | 0) + 1;
        if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
        if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
        if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
    }
    function pushUndo(label) { if (typeof window._pushLayerStackUndo === 'function') window._pushLayerStackUndo(label); }

    // ------------------------------------------------------------------ compositing
    var prevComp = window._spbCompositeLayerStack;
    // Adjustment layers (pc-adjust.js) have no pixels of their own: their mask is the strength map. {A: alpha canvas, dx, dy: where to draw it in canvas space}
    function strengthFor(L) {
        if (!L || !L.pcMask) return null;
        if (swapped && swapped.id === L.id) {   // inside _commitLayerPaint: L.img is the new mask surface
            var nb = L.bbox || [0, 0];
            return { A: effAlpha(swapped.mOld, toAlpha(flatOpaque(L.img, nb[0], nb[1]), false), true), dx: 0, dy: 0 };
        }
        var m = syncMask(L); if (!m || m.enabled === false) return null;
        var b = L.bbox || [0, 0];
        return { A: effAlpha(m, toAlpha(m.c, true)), dx: (b[0] | 0) - m.ax, dy: (b[1] | 0) - m.ay };
    }
    // a layer with a live mask -> a throw-away copy whose image is already masked (null = draw as is)
    function proxyFor(L) {
        if (!L || !L.pcMask || !L.img || L.__pcmProxy) return null;
        if (L.pcAdj) return Object.assign({}, L, { __pcmProxy: true, __pcmStrength: strengthFor(L) || false });   // adjustment layer: pc-adjust.js reads the strength
        if (swapped && swapped.id === L.id) {   // inside _commitLayerPaint: L.img is the NEW mask surface, the real art is stashed
            var nb = L.bbox || [0, 0], rb = swapped.real.bbox || [0, 0];
            var S2 = flatOpaque(L.img, nb[0], nb[1]);
            var A2 = effAlpha(swapped.mOld, toAlpha(S2, false), true);
            return Object.assign({}, L, { img: maskedImage(swapped.real.img, A2, rb[0] | 0, rb[1] | 0), bbox: swapped.real.bbox, __pcmProxy: true });
        }
        var m = syncMask(L);
        if (!m || m.enabled === false) return null;
        var A = effAlpha(m, toAlpha(m.c, true));
        return Object.assign({}, L, { img: maskedImage(L.img, A, m.ax, m.ay), __pcmProxy: true });
    }
    // the move / transform gesture fast path draws a single layer straight through _drawLayerPixelContent
    var prevDraw = window._drawLayerPixelContent;
    if (typeof prevDraw === 'function' && !prevDraw.__pcm) {
        var wdraw = function (ctx, layers, idx, so) {
            if (!off() && layers && layers[idx] && layers[idx].pcMask && !layers[idx].__pcmProxy) {
                var pr = proxyFor(layers[idx]);
                if (pr) { var l2 = layers.slice(); l2[idx] = pr; return prevDraw.call(this, ctx, l2, idx, so); }
            }
            return prevDraw.apply(this, arguments);
        };
        wdraw.__pcm = true;
        window._drawLayerPixelContent = wdraw;
        undoers.push(function () { if (window._drawLayerPixelContent === wdraw) window._drawLayerPixelContent = prevDraw; });
    }
    // mask-stroke live preview: persistent scratch canvases + work limited to the layer's own rectangle (TL-15 perf: the first version
    // allocated three 2048x2048 canvases and ran the luminance filter over all of them on every mouse move)
    // Incremental: the brush engine reports every dab rectangle (_activePaintCompositeRegion.add); only that rectangle is converted
    // to alpha and re-masked. No SVG filter on this path - a canvas filter="url(#id)" forces a document style recalculation on every
    // use, ~55-80 ms while the page has dirty inline styles (measured), which is what made mask strokes feel heavy.
    var live = { w: 0, h: 0, A: null, out: null, timer: 0, sess: null, dirty: null };
    function liveFree() { live.A = live.out = null; live.w = live.h = 0; live.timer = 0; live.sess = null; live.dirty = null; }
    function noteDirty(r) {   // every brush dab of the active paint session (mask stroke or layer stroke); sessions reset it when they start
        if (live.dirty === 'full') return;
        if (!r || !isFinite(r.x) || !isFinite(r.y) || !isFinite(r.width) || !isFinite(r.height) || r.width <= 0 || r.height <= 0) { live.dirty = 'full'; return; }
        var d = live.dirty, x0 = Math.floor(r.x), y0 = Math.floor(r.y), x1 = Math.ceil(r.x + r.width), y1 = Math.ceil(r.y + r.height);
        live.dirty = d ? { x0: Math.min(d.x0, x0), y0: Math.min(d.y0, y0), x1: Math.max(d.x1, x1), y1: Math.max(d.y1, y1) } : { x0: x0, y0: y0, x1: x1, y1: y1 };
    }
    function liveOverride(L, active) {   // mask stroke in progress: real pixels x the surface being painted (density only, no feather)
        var t0 = performance.now();
        var d = cdims(), b = L.bbox || [0, 0], m = L.pcMask;
        var real = stroke ? stroke.real : { img: L.img, bbox: b };
        var rb = real.bbox || [0, 0], rw = real.img.naturalWidth || real.img.width, rh = real.img.naturalHeight || real.img.height;
        var den = clamp01(m.density == null ? 1 : m.density);
        var x0 = Math.max(0, rb[0] | 0), y0 = Math.max(0, rb[1] | 0), x1 = Math.min(d.w, (rb[0] | 0) + rw), y1 = Math.min(d.h, (rb[1] | 0) + rh);
        var fresh = !live.sess || live.sess.st !== stroke || live.sess.active !== active || live.sess.den !== den || live.w !== d.w || live.h !== d.h || !live.out;
        if (live.w !== d.w || live.h !== d.h || !live.out) { live.w = d.w; live.h = d.h; live.A = mk(d.w, d.h); live.out = mk(d.w, d.h); }
        var og = cx(live.out), ag = cx(live.A);
        var dx0, dy0, dx1, dy1;
        if (fresh) {
            og.clearRect(0, 0, d.w, d.h); live.sess = { st: stroke, active: active, den: den }; live.dirty = null;
            dx0 = x0; dy0 = y0; dx1 = x1; dy1 = y1;
        } else {
            var dr = live.dirty; live.dirty = null;
            if (!dr) return live.out;                               // nothing painted since the last preview
            if (dr === 'full') { dx0 = x0; dy0 = y0; dx1 = x1; dy1 = y1; }
            else { dx0 = Math.max(x0, dr.x0); dy0 = Math.max(y0, dr.y0); dx1 = Math.min(x1, dr.x1); dy1 = Math.min(y1, dr.y1); }
        }
        var dw = dx1 - dx0, dh = dy1 - dy0;
        if (dw <= 0 || dh <= 0) return live.out;
        // mask surface (flattened over black) -> luminance alpha (PhotoCraft/PS mask value), density folded in: a = 1 - den (1 - m)
        var id = cx(active).getImageData(dx0, dy0, dw, dh), p = id.data, n = p.length, i, lum, al, full = den >= 0.9999;
        for (i = 0; i < n; i += 4) {
            lum = (54 * p[i] + 183 * p[i + 1] + 19 * p[i + 2]) >> 8; al = p[i + 3];
            if (al < 255) lum = lum * al / 255;
            p[i] = 0; p[i + 1] = 0; p[i + 2] = 0; p[i + 3] = full ? lum : 255 - den * (255 - lum);
        }
        ag.putImageData(id, dx0, dy0);
        if (L.pcAdj) { stats.liveN = (stats.liveN | 0) + 1; return live.A; }   // adjustment layer: the alpha map IS the preview (pc-adjust.js reads it as strength)
        var t1 = performance.now();
        og.save(); og.beginPath(); og.rect(dx0, dy0, dw, dh); og.clip();
        og.globalCompositeOperation = 'source-over'; og.clearRect(dx0, dy0, dw, dh);
        og.drawImage(real.img, dx0 - (rb[0] | 0), dy0 - (rb[1] | 0), dw, dh, dx0, dy0, dw, dh);
        og.globalCompositeOperation = 'destination-in'; og.drawImage(live.A, dx0, dy0, dw, dh, dx0, dy0, dw, dh);
        og.restore();
        if (live.timer) clearTimeout(live.timer);
        live.timer = setTimeout(liveFree, 4000);
        var t2 = performance.now();
        stats.liveN = (stats.liveN | 0) + 1; stats.liveAlphaMs = (stats.liveAlphaMs || 0) + (t1 - t0); stats.liveMaskMs = (stats.liveMaskMs || 0) + (t2 - t1);
        return live.out;
    }
    (function hookDirty() {
        var q = window._activePaintCompositeRegion;
        if (!q || typeof q.add !== 'function' || q.add.__pcm) return;
        var oadd = q.add;
        var nadd = function (rect) { try { noteDirty(rect); } catch (_e) {} return oadd.apply(this, arguments); };
        nadd.__pcm = true; q.add = nadd;
        undoers.push(function () { if (q.add === nadd) q.add = oadd; });
    })();
    var lay = { out: null, sess: null, timer: 0 };   // painting the layer's own pixels on a masked layer: incremental as well
    function layFree() { lay.out = null; lay.sess = null; lay.timer = 0; }
    function layerStrokeOverride(L, m, ov) {   // the preview still shows the mask while the layer art is being painted
        var A = effAlpha(m, toAlpha(m.c, true)), b = L.bbox || [0, 0], bx = b[0] | 0, by = b[1] | 0, W = ov.width, H = ov.height;
        var fresh = !lay.out || !lay.sess || lay.sess.ov !== ov || lay.sess.A !== A || lay.sess.bx !== bx || lay.sess.by !== by || lay.sess.ax !== m.ax || lay.sess.ay !== m.ay || lay.out.width !== W || lay.out.height !== H;
        var x0 = 0, y0 = 0, x1 = W, y1 = H;
        if (fresh) {
            if (!lay.out || lay.out.width !== W || lay.out.height !== H) lay.out = mk(W, H);
            lay.sess = { ov: ov, A: A, bx: bx, by: by, ax: m.ax, ay: m.ay }; live.dirty = null;
        } else {
            var dr = live.dirty; live.dirty = null;
            if (!dr) return lay.out;
            if (dr !== 'full') { x0 = Math.max(0, dr.x0); y0 = Math.max(0, dr.y0); x1 = Math.min(W, dr.x1); y1 = Math.min(H, dr.y1); }
        }
        var g = cx(lay.out);
        if (x1 > x0 && y1 > y0) {
            g.save(); g.beginPath(); g.rect(x0, y0, x1 - x0, y1 - y0); g.clip();
            g.globalCompositeOperation = 'source-over'; g.clearRect(x0, y0, x1 - x0, y1 - y0);
            g.drawImage(ov, x0, y0, x1 - x0, y1 - y0, x0, y0, x1 - x0, y1 - y0);
            g.globalCompositeOperation = 'destination-in'; g.drawImage(A, bx - m.ax, by - m.ay);
            g.restore();
        }
        if (lay.timer) clearTimeout(lay.timer);
        lay.timer = setTimeout(layFree, 4000);
        return lay.out;
    }
    if (typeof prevComp === 'function' && !prevComp.__pcm) {
        var wcomp = function (ctx, ls, options) {
            if (off() || !Array.isArray(ls)) return prevComp.apply(this, arguments);
            var any = false, i;
            for (i = 0; i < ls.length; i++) if (ls[i] && ls[i].pcMask) { any = true; break; }
            if (!any) return prevComp.apply(this, arguments);
            var t0 = performance.now();
            var mapped = ls.slice();
            for (i = 0; i < ls.length; i++) {
                var px = proxyFor(ls[i]);
                if (px) mapped[i] = px;
            }
            var opts = Object.assign({}, options || {});
            var po = opts.sourceOverrideFor;
            if (typeof po === 'function') {
                opts.sourceOverrideFor = function (layer, idx) {
                    var ov = po(layer, idx);
                    if (!ov) return ov;
                    var orig = ls[idx];
                    if (!orig || !orig.pcMask || !orig.img) return ov;
                    var live = (typeof _activeLayerCanvas !== 'undefined') ? _activeLayerCanvas : null;
                    if (stroke && stroke.id === orig.id && ov === live) return liveOverride(orig, ov);
                    var mm = syncMask(orig);
                    if (!mm || mm.enabled === false || (swapped && swapped.id === orig.id)) return ov;
                    return layerStrokeOverride(orig, mm, ov);
                };
            }
            var t1 = performance.now();
            var r = prevComp.call(this, ctx, mapped, opts);
            var t2 = performance.now();
            stats.composites++; stats.lastComposeMs = t2 - t0; stats.mapMs = (stats.mapMs || 0) + (t1 - t0); stats.prevMs = (stats.prevMs || 0) + (t2 - t1);
            if (stats.trace) stats.trace.push([Math.round(t1 - t0), Math.round(t2 - t1), ctx && ctx.canvas ? ctx.canvas.width : -1, ls.length]);
            return r;
        };
        wcomp.__pcm = true;
        window._spbCompositeLayerStack = wcomp;
        undoers.push(function () { if (window._spbCompositeLayerStack === wcomp) window._spbCompositeLayerStack = prevComp; });
    }

    // ------------------------------------------------------------------ mask painting through the existing brush pipeline
    var prevInit = window._initLayerPaintCanvas;
    if (typeof prevInit === 'function' && !prevInit.__pcm) {
        var winit = function () {
            var L = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
            if (!off() && L && L.pcAdj && L.img && !L.locked && editId !== L.id) {   // adjustment layers hold no pixels: the brush paints where the adjustment applies
                if (!L.pcMask) add(L.id, 'reveal');
                if (L.pcMask) setEdit(L.id, true);
            }
            if (off() || !editId || !L || L.id !== editId || !L.pcMask || !L.img || L.locked) return prevInit.apply(this, arguments);
            var m = syncMask(L);
            var Sw = aligned(L, m), real = { img: L.img, bbox: L.bbox };
            var zc = window.SPB_ZONECLIP_OFF;
            stroke = { id: L.id, real: real, Sw: Sw, mOld: m, zc: zc, initing: true };
            L.img = Sw; L.bbox = [0, 0, Sw.width, Sw.height];
            var ok = false;
            try { ok = prevInit.apply(this, arguments); }
            finally { L.img = real.img; L.bbox = real.bbox; stroke && (stroke.initing = false); }
            if (ok) { window.SPB_ZONECLIP_OFF = true; stats.strokes++; }   // a mask stroke is not clipped to the selected zone's art
            else stroke = null;
            return ok;
        };
        winit.__pcm = true;
        window._initLayerPaintCanvas = winit;
        undoers.push(function () { if (window._initLayerPaintCanvas === winit) window._initLayerPaintCanvas = prevInit; });
    }
    function endStroke() {
        if (stroke) { window.SPB_ZONECLIP_OFF = stroke.zc; }
        stroke = null;
    }
    function fixThumb(L) {
        try { if (typeof window._refreshPaintedLayerThumbnail === 'function') window._refreshPaintedLayerThumbnail(L); } catch (_e) {}
    }
    var prevCommit = window._commitLayerPaint;
    if (typeof prevCommit === 'function' && !prevCommit.__pcm) {
        var wcommit = function () {
            if (!stroke) return prevCommit.apply(this, arguments);
            var s = stroke, L = byId(s.id);
            if (!L || !L.pcMask) { endStroke(); return prevCommit.apply(this, arguments); }
            L.img = s.Sw; L.bbox = [0, 0, s.Sw.width, s.Sw.height];
            swapped = { id: L.id, real: s.real, mOld: s.mOld };
            var r;
            try { r = prevCommit.apply(this, arguments); }
            finally {
                var nImg = L.img, nBox = L.bbox;
                L.img = s.real.img; L.bbox = s.real.bbox;
                swapped = null;
                if (nImg !== s.Sw && nImg) {   // pixels changed: the committed surface becomes the new (immutable) mask
                    var S = flatOpaque(nImg, nBox ? nBox[0] : 0, nBox ? nBox[1] : 0);
                    var b = s.real.bbox || [0, 0];
                    L.pcMask = newMaskObj(L, S, { enabled: s.mOld.enabled, density: s.mOld.density, feather: s.mOld.feather, def: s.mOld.def });
                    L.pcMask = freeze(Object.assign({}, L.pcMask, { ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0 }));
                    fixThumb(L);
                    if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
                }
                endStroke();
            }
            return r;
        };
        wcommit.__pcm = true;
        window._commitLayerPaint = wcommit;
        undoers.push(function () { if (window._commitLayerPaint === wcommit) window._commitLayerPaint = prevCommit; });
    }
    var prevCancel = window._cancelLayerPaintStroke;
    if (typeof prevCancel === 'function' && !prevCancel.__pcm) {
        var wcancel = function () { var r = prevCancel.apply(this, arguments); endStroke(); return r; };
        wcancel.__pcm = true;
        window._cancelLayerPaintStroke = wcancel;
        undoers.push(function () { if (window._cancelLayerPaintStroke === wcancel) window._cancelLayerPaintStroke = prevCancel; });
    }
    // history: image entries pushed for a mask edit record the mask object they replace; undo / redo put it back
    var prevPush = window._pushLayerUndo;
    if (typeof prevPush === 'function' && !prevPush.__pcm) {
        var wpush = function (layer, label, links) {
            if (off() || !layer) return prevPush.apply(this, arguments);
            var proxyOf = layer.__pcProxyOf ? byId(layer.__pcProxyOf) : null;
            var target = proxyOf || layer;
            var forMask = !!proxyOf || (stroke && stroke.id === target.id) || (swapped && swapped.id === target.id);
            if (!forMask) {   // any other pixel edit of a masked layer (transform, flip, filter ...): remember the mask it started from
                var had = layer.pcMask || null;
                var r0 = prevPush.apply(this, arguments);
                if (had) { try { var t0 = _layerUndoStack[_layerUndoStack.length - 1]; if (t0 && t0.type === 'image' && t0.layerId === layer.id) t0.__pcMask = had; } catch (_e) {} }
                return r0;
            }
            var oldMask =(swapped && swapped.id === target.id) ? swapped.mOld : (stroke && stroke.id === target.id) ? stroke.mOld : target.pcMask;
            var keep = { img: target.img, bbox: target.bbox };
            if (swapped && swapped.id === target.id) { target.img = swapped.real.img; target.bbox = swapped.real.bbox; }
            var r;
            try { r = prevPush.call(this, target, label, links); }
            finally { target.img = keep.img; target.bbox = keep.bbox; }
            try { var top = _layerUndoStack[_layerUndoStack.length - 1]; if (top && top.type === 'image' && top.layerId === target.id) top.__pcMask = oldMask || null; } catch (_e) {}
            return r;
        };
        wpush.__pcm = true;
        window._pushLayerUndo = wpush;
        undoers.push(function () { if (window._pushLayerUndo === wpush) window._pushLayerUndo = prevPush; });
    }
    function wrapHistory(name, topOf, reEntryOf) {
        var prev = window[name];
        if (typeof prev !== 'function' || prev.__pcm) return;
        var w = function () {
            var src = topOf(), info = null;
            if (!off() && src && src.type === 'image' && Object.prototype.hasOwnProperty.call(src, '__pcMask')) {
                var L = byId(src.layerId);
                if (L) { info = { L: L, pre: L.pcMask || null }; if (src.__pcMask) L.pcMask = src.__pcMask; else delete L.pcMask; }
            }
            var r = prev.apply(this, arguments);
            if (info) {
                var made = reEntryOf();
                if (r === false) { if (info.pre) info.L.pcMask = info.pre; else delete info.L.pcMask; }
                else if (made && made.type === 'image' && made.layerId === info.L.id) made.__pcMask = info.pre;
                window._spbLayerRev = (window._spbLayerRev | 0) + 1;   // the live-composite memo is keyed on this
                if (r !== false && typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
                if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
                if (r !== false && typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
            }
            return r;
        };
        w.__pcm = true;
        window[name] = w;
        undoers.push(function () { if (window[name] === w) window[name] = prev; });
    }
    wrapHistory('undoLayerEdit', function () { return _layerUndoStack[_layerUndoStack.length - 1]; }, function () { return _layerRedoStack[_layerRedoStack.length - 1]; });
    wrapHistory('redoLayerEdit', function () { return _layerRedoStack[_layerRedoStack.length - 1]; }, function () { return _layerUndoStack[_layerUndoStack.length - 1]; });

    // gradient / bucket tools take the layer from getSelectedEditableLayer(): while a mask is being edited they get a proxy whose
    // pixels are the mask surface, and commitLayerCanvasUpdate(proxy, canvas) turns the result into the new mask.
    function callerIs(names) {
        try { var st = String(new Error().stack || ''); for (var i = 0; i < names.length; i++) if (st.indexOf(names[i]) >= 0) return true; } catch (_e) {}
        return false;
    }
    var prevEd = window.getSelectedEditableLayer;
    if (typeof prevEd === 'function' && !prevEd.__pcm) {
        var wed = function () {
            var L = prevEd.apply(this, arguments);
            if (off() || !editId || !L || L.id !== editId || !L.pcMask || stroke || swapped) return L;
            if (!callerIs(['fillGradientOnLayer', 'fillBucketOnLayer'])) return L;
            var m = syncMask(L), Sw = aligned(L, m);
            return Object.assign({}, L, { img: Sw, bbox: [0, 0, Sw.width, Sw.height], __pcProxyOf: L.id });
        };
        wed.__pcm = true;
        window.getSelectedEditableLayer = wed;
        undoers.push(function () { if (window.getSelectedEditableLayer === wed) window.getSelectedEditableLayer = prevEd; });
    }
    var prevCommitCanvas = window.commitLayerCanvasUpdate;
    if (typeof prevCommitCanvas === 'function' && !prevCommitCanvas.__pcm) {
        var wcc = function (layer, sourceCanvas, successToast) {
            if (!off() && swapped && swapped.grad && layer && layer.id === swapped.id && sourceCanvas) {   // gradient gesture on the mask
                var Lg = byId(swapped.id), rg = swapped.real, mg = swapped.mOld;
                if (Lg) {
                    Lg.img = rg.img; Lg.bbox = rg.bbox;
                    var bg = rg.bbox || [0, 0];
                    Lg.pcMask = freeze(Object.assign({}, mg, { c: flatOpaque(sourceCanvas, 0, 0), ax: bg[0] | 0, ay: bg[1] | 0, b0: bg[0] | 0, b1: bg[1] | 0, img: Lg.img }));
                    swapped = null; touch();
                    toast('Gradient applied to the layer mask', 'success');
                    return true;
                }
            }
            if (off() || !layer || !layer.__pcProxyOf || !sourceCanvas) return prevCommitCanvas.apply(this, arguments);
            var L = byId(layer.__pcProxyOf);
            if (!L || !L.pcMask) return false;
            var old = L.pcMask, b = L.bbox || [0, 0];
            var S = flatOpaque(sourceCanvas, 0, 0);
            L.pcMask = freeze(Object.assign({}, old, { c: S, ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0, img: L.img }));
            touch();
            if (successToast) toast(String(successToast).replace(/to layer:.*$/, 'to the layer mask'), 'success');
            return true;
        };
        wcc.__pcm = true;
        window.commitLayerCanvasUpdate = wcc;
        undoers.push(function () { if (window.commitLayerCanvasUpdate === wcc) window.commitLayerCanvasUpdate = prevCommitCanvas; });
    }

    // The gradient tool looks its target layer up by id (it never calls getSelectedEditableLayer), so for the length of the gradient's
    // mouse-up the layer shows the mask surface; commitLayerCanvasUpdate (above) turns the result into the new mask and puts the art back.
    function gradSwapOut() {
        if (swapped && swapped.grad) {
            var L = byId(swapped.id);
            if (L) { L.img = swapped.real.img; L.bbox = swapped.real.bbox; }
            swapped = null;
        }
    }
    var onGradUp = function () {
        try {
            if (off() || !editId || typeof canvasMode === 'undefined' || canvasMode !== 'gradient') return;
            var t = window._gradientTarget;
            if (!t || t.kind !== 'layer' || t.layerId !== editId || !window._gradientStart) return;
            var L = byId(editId);
            if (!L || !L.pcMask || !L.img || L.locked || stroke || swapped) return;
            var m = syncMask(L), Sw = aligned(L, m);
            swapped = { id: L.id, real: { img: L.img, bbox: L.bbox }, mOld: m, grad: true };
            L.img = Sw; L.bbox = [0, 0, Sw.width, Sw.height];
            setTimeout(gradSwapOut, 0);
        } catch (_e) { gradSwapOut(); }
    };
    window.addEventListener('mouseup', onGradUp, true);
    undoers.push(function () { window.removeEventListener('mouseup', onGradUp, true); gradSwapOut(); });

    // ------------------------------------------------------------------ duplicate / merge / export keep the mask meaningful
    var prevDup = window.duplicateLayer;
    if (typeof prevDup === 'function' && !prevDup.__pcm) {
        var wdup = function (layerId) {
            var src = byId(layerId);
            var r = prevDup.apply(this, arguments);
            if (!off() && r && r.id && src && src.pcMask && !r.pcMask) {
                r.pcMask = freeze(Object.assign({}, syncMask(src) || src.pcMask, { img: r.img }));
                if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
                if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
            }
            return r;
        };
        wdup.__pcm = true;
        window.duplicateLayer = wdup;
        undoers.push(function () { if (window.duplicateLayer === wdup) window.duplicateLayer = prevDup; });
    }
    function bakeLayer(L) {   // mask -> pixels (no history entry: callers snapshot first)
        var m = syncMask(L);
        if (!m) return false;
        if (m.enabled !== false && L.img) {
            var A = effAlpha(m, toAlpha(m.c, true));
            L.img = maskedImage(L.img, A, m.ax, m.ay);
            // the baked image is a derived canvas the cache must not hand out again
            maskedCache.delete ? maskedCache.delete(L.img) : null;
        }
        delete L.pcMask;
        stats.bakes++;
        return true;
    }
    var prevStackPush = window._pushLayerStackUndo;
    if (typeof prevStackPush === 'function' && !prevStackPush.__pcm) {
        var wsp = function (label) {
            var r = prevStackPush.apply(this, arguments);
            if (pendingBake && !off()) {
                var ids = pendingBake; pendingBake = null;
                ids.forEach(function (id) { var L = byId(id); if (L && L.pcMask) bakeLayer(L); });
            }
            return r;
        };
        wsp.__pcm = true;
        window._pushLayerStackUndo = wsp;
        undoers.push(function () { if (window._pushLayerStackUndo === wsp) window._pushLayerStackUndo = prevStackPush; });
    }
    var prevMerge = window.mergeLayerDown;
    if (typeof prevMerge === 'function' && !prevMerge.__pcm) {
        var wmerge = function (layerId) {
            if (!off()) {
                var s = stack(), i = s.findIndex(function (l) { return l && l.id === layerId; });
                if (i > 0 && s[i] && s[i - 1] && (s[i].pcMask || s[i - 1].pcMask)) pendingBake = [s[i].id, s[i - 1].id];
            }
            try { return prevMerge.apply(this, arguments); } finally { pendingBake = null; }
        };
        wmerge.__pcm = true;
        // keep the TL wrapper's marks
        for (var kk in prevMerge) { try { if (Object.prototype.hasOwnProperty.call(prevMerge, kk)) wmerge[kk] = prevMerge[kk]; } catch (_e) {} }
        window.mergeLayerDown = wmerge;
        undoers.push(function () { if (window.mergeLayerDown === wmerge) window.mergeLayerDown = prevMerge; });
    }
    // Merge Selected paints the masked layers through the compositor (mask applied) and keeps ONE survivor object: its mask would apply a second time
    var prevMergeSel = window.mergeSelectedLayers;
    if (typeof prevMergeSel === 'function' && !prevMergeSel.__pcm) {
        var wmsel = function () {
            var had = false;
            if (!off()) { try { had = ((typeof window._spbSelectedLayers === 'function') ? window._spbSelectedLayers() : []).some(function (l) { return l && l.pcMask; }); } catch (_e) {} }
            var r = prevMergeSel.apply(this, arguments);
            if (r && had) { var sv = byId(window._selectedLayerId); if (sv && sv.pcMask) { delete sv.pcMask; touch(); } }
            return r;
        };
        wmsel.__pcm = true;
        for (var kms in prevMergeSel) { try { if (Object.prototype.hasOwnProperty.call(prevMergeSel, kms)) wmsel[kms] = prevMergeSel[kms]; } catch (_e) {} }
        window.mergeSelectedLayers = wmsel;
        undoers.push(function () { if (window.mergeSelectedLayers === wmsel) window.mergeSelectedLayers = prevMergeSel; });
    }
    var prevExport = window.exportLayerAsPng;
    if (typeof prevExport === 'function' && !prevExport.__pcm) {
        var wexp = function (layerId) {
            var L = byId(layerId);
            if (off() || !L || !L.pcMask || L.pcMask.enabled === false) return prevExport.apply(this, arguments);
            var m = syncMask(L), keep = L.img;
            try { L.img = maskedImage(L.img, effAlpha(m, toAlpha(m.c, true)), m.ax, m.ay); return prevExport.apply(this, arguments); }
            finally { L.img = keep; }
        };
        wexp.__pcm = true;
        for (var k3 in prevExport) { try { if (Object.prototype.hasOwnProperty.call(prevExport, k3)) wexp[k3] = prevExport[k3]; } catch (_e) {} }
        window.exportLayerAsPng = wexp;
        undoers.push(function () { if (window.exportLayerAsPng === wexp) window.exportLayerAsPng = prevExport; });
    }

    // ------------------------------------------------------------------ the mask rides with the layer through flips / rotations / free transform
    function maskLocal(m, w, h) {   // the part of the mask that belongs to a w x h layer image (layer-local pixels)
        var c = mk(w, h), g = cx(c);
        g.fillStyle = (m.def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, w, h);
        g.drawImage(m.c, -m.ax, -m.ay);
        c.__pcOpaque = true; return c;
    }
    function placeLocal(Mn, bbox, def) {   // layer-local mask image -> canvas-aligned mask surface at the layer's new position
        var d = cdims(), S = mk(d.w, d.h), g = cx(S);
        g.fillStyle = (def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, d.w, d.h);
        g.drawImage(Mn, bbox[0] | 0, bbox[1] | 0);
        S.__pcOpaque = true; return S;
    }
    function setFollowed(L, m, S, bbox) {
        L.pcMask = freeze(Object.assign({}, m, { c: S, ax: bbox[0] | 0, ay: bbox[1] | 0, b0: bbox[0] | 0, b1: bbox[1] | 0, img: L.img }));
        stats.follows = (stats.follows | 0) + 1;
        touch();
    }
    var prevDestr = window._commitDestructiveLayerTransform;
    if (typeof prevDestr === 'function' && !prevDestr.__pcm) {
        var wdestr = function (layer, candidate, nextBbox, label) {
            var m = (!off() && layer && layer.pcMask) ? syncMask(layer) : null;
            var oldImg = layer && layer.img;
            var r = prevDestr.apply(this, arguments);
            if (m && r && layer.img === candidate && oldImg && candidate !== oldImg) {
                var ow = oldImg.naturalWidth || oldImg.width, oh = oldImg.naturalHeight || oldImg.height, nw = candidate.width, nh = candidate.height;
                var lab = String(label || ''), Ml = maskLocal(m, ow, oh), Mn = mk(nw, nh), g = cx(Mn), ok = true;
                g.fillStyle = (m.def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, nw, nh);
                if (/flip horizontal/.test(lab)) { g.translate(nw, 0); g.scale(-1, 1); g.drawImage(Ml, 0, 0); }
                else if (/flip vertical/.test(lab)) { g.translate(0, nh); g.scale(1, -1); g.drawImage(Ml, 0, 0); }
                else if (/rotate 90/.test(lab)) { g.translate(nw / 2, nh / 2); g.rotate(Math.PI / 2); g.drawImage(Ml, -ow / 2, -oh / 2); }
                else if (/rotate -90/.test(lab)) { g.translate(nw / 2, nh / 2); g.rotate(-Math.PI / 2); g.drawImage(Ml, -ow / 2, -oh / 2); }
                else ok = false;
                if (ok) setFollowed(layer, m, placeLocal(Mn, layer.bbox, m.def), layer.bbox);
            }
            return r;
        };
        wdestr.__pcm = true;
        window._commitDestructiveLayerTransform = wdestr;
        undoers.push(function () { if (window._commitDestructiveLayerTransform === wdestr) window._commitDestructiveLayerTransform = prevDestr; });
    }
    var prevCT = window.commitLayerTransform;
    if (typeof prevCT === 'function' && !prevCT.__pcm) {
        var wct = function () {
            var s = window.freeTransformState, L = (!off() && s && s.target === 'layer' && !s.subRect && !s.quad) ? byId(s.layerId) : null;
            var m = (L && L.pcMask) ? syncMask(L) : null, pre = null;
            if (m && L.img) pre = { img: L.img, ow: L.img.naturalWidth || L.img.width, oh: L.img.naturalHeight || L.img.height, rot: Number(s.rotation) || 0, fh: (s.scaleX || 1) < 0, fv: (s.scaleY || 1) < 0, nW: Math.round(s.boxW), nH: Math.round(s.boxH), id: L.id };
            var r = prevCT.apply(this, arguments);
            if (pre) {
                var L2 = byId(pre.id);
                if (L2 && L2.img && L2.img !== pre.img) {
                    var nw = L2.img.width, nh = L2.img.height;
                    if (!pre.rot && !pre.fh && !pre.fv && nw === pre.ow && nh === pre.oh) {   // pure move: the same mask pixels, new place
                        var bb = L2.bbox || [0, 0];
                        L2.pcMask = freeze(Object.assign({}, m, { b0: bb[0] | 0, b1: bb[1] | 0, img: L2.img }));
                        stats.follows = (stats.follows | 0) + 1; touch();
                    } else {   // scale / rotate / flip: the mask goes through the same affine as the pixels
                        var Ml = maskLocal(m, pre.ow, pre.oh), Mn = mk(nw, nh), g = cx(Mn);
                        g.fillStyle = (m.def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, nw, nh);
                        g.translate(nw / 2, nh / 2);
                        if (pre.fh || pre.fv) g.scale(pre.fh ? -1 : 1, pre.fv ? -1 : 1);
                        if (pre.rot) g.rotate(pre.rot * Math.PI / 180);
                        g.drawImage(Ml, -pre.nW / 2, -pre.nH / 2, pre.nW, pre.nH);
                        setFollowed(L2, m, placeLocal(Mn, L2.bbox, m.def), L2.bbox);
                    }
                }
            }
            return r;
        };
        wct.__pcm = true;
        window.commitLayerTransform = wct;
        undoers.push(function () { if (window.commitLayerTransform === wct) window.commitLayerTransform = prevCT; });
    }

    // Mirror clone (the iRacing "other side of the car" button): the clone's mask is the mirrored mask
    var prevMirror = window.mirrorCloneLayer;
    if (typeof prevMirror === 'function' && !prevMirror.__pcm) {
        var wmirror = function (layerId) {
            var src = byId(layerId), m = (!off() && src && src.pcMask) ? syncMask(src) : null, before = {};
            stack().forEach(function (l) { before[l.id] = 1; });
            var r = prevMirror.apply(this, arguments);
            if (m && src && src.img) {
                var nl = null, s2 = stack();
                for (var i = 0; i < s2.length; i++) if (!before[s2[i].id] && /^psd_mirror_/.test(String(s2[i].id))) nl = s2[i];
                if (nl && nl.img) {
                    var ow = src.img.naturalWidth || src.img.width, oh = src.img.naturalHeight || src.img.height;
                    var Ml = maskLocal(m, ow, oh), Mn = mk(nl.img.width, nl.img.height), g = cx(Mn);
                    g.fillStyle = (m.def >= 128) ? '#fff' : '#000'; g.fillRect(0, 0, Mn.width, Mn.height);
                    g.translate(Mn.width, 0); g.scale(-1, 1); g.drawImage(Ml, 0, 0);
                    var bb = nl.bbox || [0, 0];
                    nl.pcMask = freeze({ c: placeLocal(Mn, bb, m.def), ax: bb[0] | 0, ay: bb[1] | 0, b0: bb[0] | 0, b1: bb[1] | 0, img: nl.img, enabled: m.enabled, density: m.density, feather: m.feather, def: m.def });
                    touch();
                }
            }
            return r;
        };
        wmirror.__pcm = true;
        window.mirrorCloneLayer = wmirror;
        undoers.push(function () { if (window.mirrorCloneLayer === wmirror) window.mirrorCloneLayer = prevMirror; });
    }

    // ------------------------------------------------------------------ actions (each one history step)
    function selectionCoverage(w, h) {
        try { var cov = (typeof window._activeSelectionMask === 'function') ? window._activeSelectionMask(w, h, false) : null; return (cov && cov.length === w * h) ? cov : null; } catch (_e) { return null; }
    }
    function greyFromCoverage(cov, w, h, invert) {
        var c = mk(w, h), g = cx(c), id = g.createImageData(w, h), d = id.data;
        for (var i = 0, p = 0; i < cov.length; i++, p += 4) { var v = cov[i]; if (invert) v = 255 - v; d[p] = d[p + 1] = d[p + 2] = v; d[p + 3] = 255; }
        g.putImageData(id, 0, 0); c.__pcOpaque = true; return c;
    }
    function add(id, kind, quiet) {   // quiet: caller owns the history step and the recomposite (adjustment layers create theirs together)
        var L = byId(id);
        if (!L || !L.img) return false;
        if (L.locked) { toast('"' + (L.name || 'Layer') + '" is locked, unlock it to add a mask', 'warn'); return false; }
        if (L.pcMask) { if (!quiet) toast('"' + (L.name || 'Layer') + '" already has a mask', 'info'); return false; }
        var d = cdims(), S, def = 255;
        if (kind === 'selection' || kind === 'hide-selection') {
            var cov = selectionCoverage(d.w, d.h);
            if (!cov) { toast('Make a selection first (use Select, or a zone region), then add the mask from it', 'warn'); return false; }
            S = greyFromCoverage(cov, d.w, d.h, kind === 'hide-selection');
            def = kind === 'hide-selection' ? 255 : 0;
        } else {
            def = kind === 'hide' ? 0 : 255;
            S = mk(d.w, d.h); var g = cx(S); g.fillStyle = def ? '#fff' : '#000'; g.fillRect(0, 0, d.w, d.h); S.__pcOpaque = true;
        }
        if (!quiet) pushUndo('add layer mask');
        L.pcMask = newMaskObj(L, S, { def: def });
        stats.adds++;
        if (!quiet) touch();
        return true;
    }
    function remove(id) {
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        pushUndo('delete layer mask');
        if (editId === id) exitEdit();
        delete L.pcMask; touch(); return true;
    }
    function invert(id) {
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var m = syncMask(L), S0 = aligned(L, m), S = mk(S0.width, S0.height), g = cx(S);
        g.fillStyle = '#fff'; g.fillRect(0, 0, S.width, S.height); g.globalCompositeOperation = 'difference'; g.drawImage(S0, 0, 0); S.__pcOpaque = true;
        pushUndo('invert layer mask');
        var b = L.bbox || [0, 0];
        L.pcMask = freeze(Object.assign({}, m, { c: S, ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0, def: 255 - m.def }));
        touch(); return true;
    }
    function setEnabled(id, on) {
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var m = syncMask(L); if ((m.enabled !== false) === !!on) return true;
        pushUndo((on ? 'enable' : 'disable') + ' layer mask');
        L.pcMask = freeze(Object.assign({}, m, { enabled: !!on })); touch(); return true;
    }
    function applyMask(id) {
        var L = byId(id); if (!L || !L.pcMask || !L.img) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var m = syncMask(L);
        pushUndo('apply layer mask');
        if (editId === id) exitEdit();
        var out = (m.enabled !== false) ? maskedImage(L.img, effAlpha(m, toAlpha(m.c, true)), m.ax, m.ay) : L.img;
        var b = L.bbox || [0, 0], d = cdims(), full = mk(d.w, d.h), g = cx(full);
        g.drawImage(out, b[0] | 0, b[1] | 0);
        var crop = (typeof window._tightCropLayerCanvas === 'function') ? window._tightCropLayerCanvas(full) : null;
        if (crop && crop.canvas) { L.img = crop.canvas; L.bbox = crop.bbox; }
        else { var e = mk(1, 1); L.img = e; L.bbox = [0, 0, 1, 1]; }
        delete L.pcMask; stats.bakes++;
        touch(); toast('Mask applied to the layer pixels'); return true;
    }
    function fill(id, white) {
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var m = syncMask(L), d = cdims(), S = mk(d.w, d.h), g = cx(S), b = L.bbox || [0, 0];
        g.fillStyle = white ? '#fff' : '#000'; g.fillRect(0, 0, d.w, d.h); S.__pcOpaque = true;
        pushUndo(white ? 'reveal all (layer mask)' : 'hide all (layer mask)');
        L.pcMask = freeze(Object.assign({}, m, { c: S, ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0, def: white ? 255 : 0 }));
        touch(); return true;
    }
    function fade(id, dir) {   // multiply a white->black ramp across the layer's own bounds into the mask
        var L = byId(id); if (!L || !L.pcMask || !L.img) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        var m = syncMask(L), S0 = aligned(L, m), d = cdims(), b = L.bbox || [0, 0, d.w, d.h];
        var x0 = b[0], y0 = b[1], x1 = b[0] + (L.img.naturalWidth || L.img.width), y1 = b[1] + (L.img.naturalHeight || L.img.height);
        var G = mk(d.w, d.h), g = cx(G); g.fillStyle = '#fff'; g.fillRect(0, 0, d.w, d.h);
        var lg;
        if (dir === 'right') lg = g.createLinearGradient(x0, 0, x1, 0);
        else if (dir === 'left') lg = g.createLinearGradient(x1, 0, x0, 0);
        else if (dir === 'down') lg = g.createLinearGradient(0, y0, 0, y1);
        else lg = g.createLinearGradient(0, y1, 0, y0);
        lg.addColorStop(0, '#fff'); lg.addColorStop(1, '#000');
        g.fillStyle = lg; g.fillRect(x0, y0, x1 - x0, y1 - y0);
        var S = mk(d.w, d.h), s = cx(S); s.drawImage(S0, 0, 0); s.globalCompositeOperation = 'multiply'; s.drawImage(G, 0, 0); S.__pcOpaque = true;
        pushUndo('fade layer mask');
        L.pcMask = freeze(Object.assign({}, m, { c: S, ax: b[0] | 0, ay: b[1] | 0, b0: b[0] | 0, b1: b[1] | 0 }));
        touch(); return true;
    }
    function setProp(id, field, v, final) {   // density / feather sliders: one history step per drag
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) return false;
        var m = syncMask(L);
        if (!gesture || gesture.id !== id || gesture.field !== field) { pushUndo('layer mask ' + field); gesture = { id: id, field: field }; }
        var o = {}; o[field] = field === 'density' ? clamp01(v) : Math.max(0, Math.min(250, Number(v) || 0));
        L.pcMask = freeze(Object.assign({}, m, o));
        window._spbLayerRev = (window._spbLayerRev | 0) + 1;
        if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
        if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
        if (final) { gesture = null; if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel(); }
        return true;
    }
    function setEdit(id, on) {
        if (!on) { exitEdit(); if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel(); return true; }
        var L = byId(id); if (!L || !L.pcMask) return false;
        if (L.locked) { toast('Layer is locked', 'warn'); return false; }
        if (editId && editId !== id) exitEdit();
        if (typeof window.selectPSDLayer === 'function' && window._selectedLayerId !== id) { try { window.selectPSDLayer(id); } catch (_e) {} }
        editId = id;
        savedColors = { fg: typeof _foregroundColor === 'string' ? _foregroundColor : null, bg: typeof _backgroundColor === 'string' ? _backgroundColor : null };
        try { if (typeof window.setForegroundColor === 'function') window.setForegroundColor('#ffffff'); if (typeof window.setBackgroundColor === 'function') window.setBackgroundColor('#000000'); } catch (_e) {}
        toast('Painting the layer mask: white reveals, black hides, the Eraser hides', 'info');
        if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
        return true;
    }
    function exitEdit() {
        if (!editId) return;
        editId = null;
        if (savedColors) {
            try { if (savedColors.fg && typeof window.setForegroundColor === 'function') window.setForegroundColor(savedColors.fg); if (savedColors.bg && typeof window.setBackgroundColor === 'function') window.setBackgroundColor(savedColors.bg); } catch (_e) {}
        }
        savedColors = null;
    }

    // ------------------------------------------------------------------ persistence (project save / load)
    var pngCache = new WeakMap();   // the surface is immutable, so one encode per committed mask serves every autosave
    function serialize(layer) {
        var m = layer && layer.pcMask; if (!m || !m.c) return undefined;
        try {
            var png = pngCache.get(m.c);
            if (!png) { png = m.c.toDataURL('image/png'); pngCache.set(m.c, png); }
            return { v: 1, png: png, ax: m.ax, ay: m.ay, enabled: m.enabled !== false, density: m.density, feather: m.feather, def: m.def };
        } catch (_e) { return undefined; }
    }
    function deserialize(layer, rec, done) {
        if (!rec || !rec.png || !layer) { if (done) done(false); return; }
        var im = new Image();
        im.onload = function () {
            var d = cdims(), S = mk(d.w, d.h), g = cx(S); g.drawImage(im, 0, 0); S.__pcOpaque = true;
            var b = layer.bbox || [0, 0];
            layer.pcMask = freeze({ c: S, ax: Number(rec.ax) || 0, ay: Number(rec.ay) || 0, b0: b[0] | 0, b1: b[1] | 0, img: layer.img, enabled: rec.enabled !== false, density: rec.density == null ? 1 : clamp01(rec.density), feather: Number(rec.feather) || 0, def: rec.def === 0 ? 0 : 255 });
            if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
            if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
            if (done) done(true);
        };
        im.onerror = function () { if (done) done(false); };
        im.src = rec.png;
    }

    // ------------------------------------------------------------------ card UI
    var BTN = 'font-size:9px;padding:2px 5px;background:#1a1a1a;color:#ccc;border:1px solid #444;border-radius:3px;cursor:pointer;line-height:1.2;';
    function el(tag, css, text, attrs) {
        var e = document.createElement(tag); if (css) e.style.cssText = css; if (text != null) e.textContent = text;
        if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
        return e;
    }
    function btn(label, act, id, title, extra) {
        var b = el('button', BTN + (extra || ''), label, { type: 'button', 'class': 'layer-act-btn', 'data-pcm': act, 'data-pcm-id': id, title: title || '' });
        return b;
    }
    function thumb(m, size, editing) {
        var c = el('canvas', 'width:' + size + 'px;height:' + size + 'px;border:1px solid ' + (editing ? '#00e5ff' : '#555') + ';border-radius:2px;background:#000;flex:0 0 auto;image-rendering:auto;' + (m.enabled === false ? 'opacity:0.35;' : 'cursor:pointer;'), null, { 'data-pcm': 'edit-toggle', title: m.enabled === false ? 'Mask is off' : 'Click to paint this mask' });
        c.width = size; c.height = size;
        try { var g = c.getContext('2d'); g.drawImage(m.c, 0, 0, size, size); } catch (_e) {}
        return c;
    }
    // The card is a 3-column grid in the clean look: a div whose direct children are .layer-act-btn dissolves into the grid
    // (display: contents), so the buttons below sit in the same columns as Dupe / Mirror / Stroke FX.
    function btnGroup(buttons) {
        var g = el('div', 'display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;');
        buttons.forEach(function (b) { g.appendChild(b); });
        return g;
    }
    function maskRows(L) {
        var rows = [];
        var m = L.pcMask, editing = editId === L.id;
        var head = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-height:20px;', null, { 'data-pcm-row': L.id });
        head.appendChild(el('span', 'font-size:8px;color:#888;flex:0 0 42px;min-width:42px;white-space:nowrap;', 'Mask:'));
        if (m) {
            var th = thumb(m, 26, editing); th.setAttribute('data-pcm-id', L.id); head.appendChild(th);
            head.appendChild(el('span', 'font-size:8px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:' + (editing ? '#00e5ff' : (m.enabled === false ? '#e88' : '#888')), editing ? 'editing' : (m.enabled === false ? 'off' : 'on')));
        } else {
            head.appendChild(el('span', 'font-size:8px;color:#888;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', 'none'));
        }
        rows.push(head);
        if (!m) {
            rows.push(btnGroup([
                btn('+ Mask', 'add-reveal', L.id, 'Add a layer mask that shows everything (paint black to hide parts, non-destructive)'),
                btn('Hide all', 'add-hide', L.id, 'Add a layer mask that hides everything (paint white to reveal parts)'),
                btn('From sel', 'add-sel', L.id, 'Add a mask that shows only the current selection')]));
            return rows;
        }
        rows.push(btnGroup([
            btn(editing ? 'Done' : 'Edit', 'edit', L.id, editing ? 'Stop painting the mask' : 'Paint the mask: Brush white reveals, black hides, the Eraser hides', editing ? 'background:#0b3a44;color:#00e5ff;border-color:#00e5ff;' : ''),
            btn('Invert', 'invert', L.id, 'Swap what is shown and what is hidden'),
            btn(m.enabled === false ? 'Disabled' : 'Enabled', 'toggle', L.id, 'Turn the mask off / on without losing it', m.enabled === false ? 'color:#e88;' : ''),
            L.pcAdj ? null : btn('Apply', 'apply', L.id, 'Bake the mask into the layer pixels and remove it'),
            btn('Remove', 'delete', L.id, 'Delete the mask (the layer comes back whole)', 'color:#f0a0a2;')].filter(Boolean)));
        function slider(label, field, min, max, step, val, unit) {
            var r = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
            r.appendChild(el('span', 'font-size:8px;color:#888;flex:0 0 42px;min-width:42px;white-space:nowrap;', label));
            var inp = el('input', 'flex:1 1 0%;min-width:0;width:0;height:12px;cursor:pointer;', null, { type: 'range', min: min, max: max, step: step, value: val, 'data-pcm-range': field, 'data-pcm-id': L.id, 'aria-label': 'Layer mask ' + label.replace(':', ''), title: 'Layer mask ' + label.replace(':', '') });
            var num = el('span', 'font-size:8px;color:#ddd;flex:0 0 34px;text-align:right;white-space:nowrap;', val + unit, { 'data-pcm-val': field });
            r.appendChild(inp); r.appendChild(num); return r;
        }
        rows.push(slider('Density:', 'density', 0, 100, 1, Math.round(clamp01(m.density) * 100), '%'));
        rows.push(slider('Feather:', 'feather', 0, 100, 1, Math.round(m.feather || 0), ' px'));
        if (editing) {
            rows.push(btnGroup([
                btn('White', 'fg-white', L.id, 'Brush reveals (white); the Eraser hides'),
                btn('Black', 'fg-black', L.id, 'Brush hides (black)'),
                btn('Fade →', 'fade-right', L.id, 'Fade the layer out toward the right'),
                btn('Fade ←', 'fade-left', L.id, 'Fade the layer out toward the left'),
                btn('Fade ↓', 'fade-down', L.id, 'Fade the layer out toward the bottom'),
                btn('Fade ↑', 'fade-up', L.id, 'Fade the layer out toward the top')]));
        }
        return rows;
    }
    function decorate() {
        if (off()) return;
        var panel = document.getElementById('layerPanelContent');
        if (!panel) return;
        wirePanel(panel);
        var sels = panel.querySelectorAll('select[data-layer-blend-control]');
        for (var i = 0; i < sels.length; i++) {
            var id = sels[i].getAttribute('data-layer-blend-control'), L = byId(id);
            if (!L) continue;
            var blendRow = sels[i].parentElement;
            if (!blendRow || (blendRow.nextElementSibling && blendRow.nextElementSibling.hasAttribute('data-pcm-row'))) continue;
            var at = blendRow.nextSibling;
            maskRows(L).forEach(function (r) { blendRow.parentNode.insertBefore(r, at); });
        }
        // mask thumbnails beside the layer thumbnails
        var s = stack();
        for (var j = 0; j < s.length; j++) {
            var l = s[j]; if (!l || !l.pcMask) continue;
            var t = document.getElementById('layerThumb_' + l.id);
            if (!t || (t.nextElementSibling && t.nextElementSibling.hasAttribute('data-pcm-rowthumb'))) continue;
            var mt = thumb(l.pcMask, 18, editId === l.id);
            mt.setAttribute('data-pcm-rowthumb', '1'); mt.setAttribute('data-pcm-id', l.id);
            mt.style.marginLeft = '-2px';
            t.parentNode.insertBefore(mt, t.nextSibling);
        }
    }
    var wired = [];
    function wirePanel(panel) {
        if (panel.__pcmWired === wired) return;
        if (typeof panel.__pcmOff === 'function') { try { panel.__pcmOff(); } catch (_e) {} }   // a previous instance of this module (hot reload)
        panel.__pcmWired = wired;
        var hs = [];
        var on = function (type, fn) { panel.addEventListener(type, fn, true); hs.push([type, fn]); };
        panel.__pcmOff = function () { hs.forEach(function (h) { panel.removeEventListener(h[0], h[1], true); }); hs = []; panel.__pcmWired = null; panel.__pcmOff = null; };
        wired.push(panel);
        on('click', function (ev) {
            var t = ev.target && ev.target.closest ? ev.target.closest('[data-pcm]') : null;
            if (!t || off()) return;
            ev.stopPropagation(); ev.preventDefault();
            var act = t.getAttribute('data-pcm'), id = t.getAttribute('data-pcm-id') || (window._selectedLayerId);
            if (act === 'add-reveal') add(id, 'reveal');
            else if (act === 'add-hide') add(id, 'hide');
            else if (act === 'add-sel') add(id, 'selection');
            else if (act === 'edit' || act === 'edit-toggle') setEdit(id, editId !== id);
            else if (act === 'invert') invert(id);
            else if (act === 'toggle') { var L = byId(id); setEnabled(id, !(L && L.pcMask && L.pcMask.enabled !== false)); }
            else if (act === 'apply') applyMask(id);
            else if (act === 'delete') remove(id);
            else if (act === 'fg-white') { try { window.setForegroundColor('#ffffff'); window.setBackgroundColor('#000000'); } catch (_e) {} }
            else if (act === 'fg-black') { try { window.setForegroundColor('#000000'); window.setBackgroundColor('#ffffff'); } catch (_e) {} }
            else if (act.indexOf('fade-') === 0) fade(id, act.slice(5));
        }, true);
        panel.addEventListener('input', function (ev) {
            var t = ev.target; if (!t || !t.getAttribute || off()) return;
            var f = t.getAttribute('data-pcm-range'); if (!f) return;
            var id = t.getAttribute('data-pcm-id'), v = Number(t.value);
            var lab = t.parentNode.querySelector('[data-pcm-val]'); if (lab) lab.textContent = (f === 'density' ? v + '%' : v + ' px');
            setProp(id, f, f === 'density' ? v / 100 : v, false);
        }, true);
        panel.addEventListener('change', function (ev) {
            var t = ev.target; if (!t || !t.getAttribute || off()) return;
            var f = t.getAttribute('data-pcm-range'); if (!f) return;
            gesture = null; if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
        }, true);
    }
    var prevPanel = window.renderLayerPanel;
    if (typeof prevPanel === 'function' && !prevPanel.__pcm) {
        var wpanel = function () {
            if (editId && (off() || window._selectedLayerId !== editId || !byId(editId) || !byId(editId).pcMask)) exitEdit();
            var r = prevPanel.apply(this, arguments);
            try { decorate(); } catch (e) { try { console.warn('[pcm] decorate failed', e); } catch (_e) {} }
            return r;
        };
        wpanel.__pcm = true;
        for (var kp in prevPanel) { try { if (Object.prototype.hasOwnProperty.call(prevPanel, kp)) wpanel[kp] = prevPanel[kp]; } catch (_e2) {} }
        window.renderLayerPanel = wpanel;
        undoers.push(function () { if (window.renderLayerPanel === wpanel) window.renderLayerPanel = prevPanel; });
    }

    window.SPBPcLayerMask = {
        version: VERSION, stats: stats, off: off,
        add: add, remove: remove, invert: invert, setEnabled: setEnabled, apply: applyMask, fill: fill, fade: fade, setProp: setProp, setEdit: setEdit,
        editing: function () { return editId; }, bake: bakeLayer, serialize: serialize, deserialize: deserialize, decorate: decorate,
        strengthFor: strengthFor,
        alphaOf: function (L) { var m = L && syncMask(L); return m ? effAlpha(m, toAlpha(m.c, true)) : null; },
        uninstall: function () {
            undoers.splice(0).reverse().forEach(function (f) { try { f(); } catch (_e) {} });
            wired.splice(0).forEach(function (p) { try { if (p.__pcmOff) p.__pcmOff(); } catch (_e) {} });
            exitEdit(); delete window.SPBPcLayerMask;
        }
    };
})();
