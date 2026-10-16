/* [SPB-TLAY 2026-10-09] TOOLS-LAYERS lane: layers panel + layer card fixes (audit: _easy_claude_work/tools_port/layers/AUDIT.md).
 *
 * Loaded AFTER paint-booth-3-canvas.js. Every change wraps/overrides a global function so the big shared files stay untouched.
 * Kill switch: window.SPB_TLAY_OFF = true (or localStorage SPB_TLAY_OFF = '1') -> every wrapper below calls straight through to the original.
 *
 *   TL-01 perf   renderLayerPanel() always ended with refreshZoneDetailIfOpen() = a full 177 ms renderZoneDetail() even when nothing the
 *                zone detail shows (layer list names/groups/visibility, the zone's restrict-to-layer set) had changed. Select / eye / blend /
 *                typing in the filter box all paid it. Now skipped when a cheap fingerprint of exactly those inputs is unchanged.
 *   TL-02 stroke Stroke FX ignored its colour (it re-drew the layer's own pixels dilated) and "Inside" / "Center" painted the whole layer.
 *                Now a real band: outside = dilate - shape, inside = shape - erode, center = half/half, filled with the chosen colour.
 *   TL-03 fx     Color Overlay / Stroke / Drop Shadow / Outer Glow / Bevel ignored the LAYER's opacity and blend mode (Photoshop: layer
 *                opacity and blend apply to the layer and its styles as a unit). Overlay is now baked into the layer pixels before the layer is
 *                drawn (so a 20% layer gets a 20% overlay); the other effects are composited with the layer's opacity and blend mode.
 *   TL-04 export EXPORT wrote the bare pixels (+HSB) and dropped every effect. Now bakes stroke / overlay / shadow / glow / bevel, on a canvas
 *                padded so a stroke or glow is not clipped at the layer edge.
 *   TL-05 merge  Merge Down into a HIDDEN lower layer silently deleted the upper layer's pixels and said "Layers merged". Now refused with
 *                a toast (true no-op, same contract as the existing hidden-upper refusal).
 *   TL-09 opacity Clearing the opacity number box applied 0% live. Empty input is ignored and the box restores its value on blur.
 *   TL-17 card   The selected layer card squeezed its name to 0 px; the row now wraps (name >= 84 px, badges on a second line).
 *   TL-10 names  Duplicate twice -> two layers called "X copy". Now "X copy", "X copy 2", "X copy 3" (and "(mirror)", "(mirror 2)").
 */
(function () {
    'use strict';
    var lsOff = false;
    try { lsOff = localStorage.getItem('SPB_TLAY_OFF') === '1'; } catch (_e) { }
    if (lsOff && window.SPB_TLAY_OFF !== true) window.SPB_TLAY_OFF = true;
    function off() { return window.SPB_TLAY_OFF === true; }
    var stats = { zoneRefreshSkipped: 0, zoneRefreshRan: 0, overlayBaked: 0, strokeDrawn: 0, exportFx: 0, mergeHiddenRefused: 0 };

    function toast(msg, kind) { try { if (typeof showToast === 'function') showToast(msg, kind); } catch (_e) { } }
    function dimsOf(img) { return { w: (img && (img.width || img.naturalWidth)) || 0, h: (img && (img.height || img.naturalHeight)) || 0 }; }
    function mk(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }

    // ---------------------------------------------------------------- TL-01 zone-detail refresh skip
    var lastZoneFp = null;
    function zoneFpNow() {
        var zi = (typeof selectedZoneIndex !== 'undefined') ? selectedZoneIndex : null;
        var z = (typeof zones !== 'undefined' && Array.isArray(zones) && typeof zi === 'number') ? zones[zi] : null;
        var ids = '', idSet = {};
        try {
            if (z) {
                ids = (Array.isArray(z.sourceLayers) && z.sourceLayers.length ? z.sourceLayers.join(',') : '') + '#' + (z.sourceLayer || '');
                if (Array.isArray(z.sourceLayers)) z.sourceLayers.forEach(function (i) { idSet[i] = 1; });
                if (z.sourceLayer) idSet[z.sourceLayer] = 1;
            }
        } catch (_e) { }
        var L = (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : [];
        var parts = new Array(L.length);
        for (var i = 0; i < L.length; i++) {
            var l = L[i];
            // visibility only matters for the layers this zone is restricted to (the "Hidden (not painting)" warning)
            parts[i] = l ? (l.id + '\u0001' + l.name + '\u0001' + l.groupName + '\u0001' + (l.img ? 1 : 0) + (idSet[l.id] ? (l.visible === false ? 'h' : 'v') : '')) : '';
        }
        return zi + '|' + ids + '|' + parts.join('\u0002');
    }
    // The zone modules install (and re-install) their window.* functions AFTER this script loads, so wrap lazily: now, on every
    // renderLayerPanel(), and on a short poll. Idempotent (the __tlay mark) and safe against a later override replacing the wrapper.
    function wrapZoneDetail() {
        var oRender = window.renderZoneDetail;
        if (typeof oRender === 'function' && !oRender.__tlay) {
            var wr = function () {
                var r = oRender.apply(this, arguments);
                try { lastZoneFp = zoneFpNow(); } catch (_e) { lastZoneFp = null; }
                return r;
            };
            wr.__tlay = true;
            window.renderZoneDetail = wr;
        }
        var oRefresh = window.refreshZoneDetailIfOpen;
        if (typeof oRefresh === 'function' && !oRefresh.__tlay) {
            var wf = function () {
                if (!off() && lastZoneFp !== null) {
                    var fp = null;
                    try { fp = zoneFpNow(); } catch (_e) { fp = null; }
                    if (fp !== null && fp === lastZoneFp) { stats.zoneRefreshSkipped++; return; }
                }
                stats.zoneRefreshRan++;
                return oRefresh.apply(this, arguments);
            };
            wf.__tlay = true;
            window.refreshZoneDetailIfOpen = wf;
        }
    }
    wrapZoneDetail();
    (function pollWrap() {
        var n = 0;
        var iv = setInterval(function () { wrapZoneDetail(); wrapFlow(); if (++n >= 40) clearInterval(iv); }, 500);
    })();
    // [SPB-TLAY 2026-10-10 TL-17] The SELECTED layer card squeezed its own name to 0 px (nowrap row: eye 19 + thumb 30 + mask 18 + opacity 22 + zone
    // badge 14 + material chip 18 + alpha/clip/lock 60 = the whole 199 px row; measured name width 0 at 1920 and 101-127 px for the unselected rows).
    // Now the selected row wraps: name gets a line share of at least 84 px, the badges/toggles drop to a second line, right aligned.
    // The rule only applies while #layerPanelContent carries data-tlay-card="1" (set after every renderLayerPanel, removed by SPB_TLAY_OFF).
    (function cardCss() {
        if (document.getElementById('spb-tlay-card-css')) return;
        var st = document.createElement('style'); st.id = 'spb-tlay-card-css';
        st.textContent = '#layerPanelContent[data-tlay-card="1"] .layer-row.selected{flex-wrap:wrap !important;justify-content:flex-end !important;row-gap:3px !important}' +
            '#layerPanelContent[data-tlay-card="1"] .layer-row.selected .layer-name-wrap{flex:1 1 84px !important;min-width:84px !important}';
        (document.head || document.documentElement).appendChild(st);
    })();
    function markCardWrap() {
        try {
            var pnl = document.getElementById('layerPanelContent');
            if (!pnl) return;
            if (off()) pnl.removeAttribute('data-tlay-card'); else pnl.setAttribute('data-tlay-card', '1');
        } catch (_e) { }
    }
    markCardWrap();
    var origRLP = window.renderLayerPanel;
    if (typeof origRLP === 'function' && !origRLP.__tlay) {
        var wrlp = function () {
            if (!off()) { wrapZoneDetail(); wrapFlow(); }
            var r = origRLP.apply(this, arguments);
            markCardWrap();
            if (!off()) paintFxLabel();
            return r;
        };
        wrlp.__tlay = true;
        window.renderLayerPanel = wrlp;
    }

    // ---------------------------------------------------------------- shared helpers for TL-02 / TL-03
    var BLENDS = { 'source-over': 1, multiply: 1, screen: 1, overlay: 1, darken: 1, lighten: 1, 'color-dodge': 1, 'color-burn': 1, 'hard-light': 1, 'soft-light': 1, difference: 1, exclusion: 1, hue: 1, saturation: 1, color: 1, luminosity: 1, lighter: 1 };
    function layerOpacity(layer) { var o = (layer.opacity != null ? layer.opacity : 255) / 255; return o < 0 ? 0 : (o > 1 ? 1 : o); }
    function layerBlend(layer) { var b = layer.blendMode || 'source-over'; return BLENDS[b] ? b : 'source-over'; }
    function adjustFilter(layer) {
        var api = window.SPBLayerClippingMask;
        return (api && typeof api.adjustFilterFor === 'function') ? api.adjustFilterFor(layer) : null;
    }
    var scratchPool = {};
    function scratchSized(tag, w, h) {
        var k = tag + w + 'x' + h;
        var c = scratchPool[k];
        if (!c) {
            var keys = Object.keys(scratchPool);
            if (keys.length > 8) delete scratchPool[keys[0]];
            c = scratchPool[k] = mk(w, h);
        }
        return c;
    }
    function resetCtx(x, w, h) {
        x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none';
        x.shadowColor = 'transparent'; x.shadowBlur = 0; x.shadowOffsetX = 0; x.shadowOffsetY = 0;
        x.clearRect(0, 0, w, h);
    }

    // ---------------------------------------------------------------- TL-03 colour overlay baked into the layer pixels
    var baked = (typeof WeakSet === 'function') ? new WeakSet() : null;
    function bakeOverlay(srcImg, layer, co) {
        var d = dimsOf(srcImg);
        if (!d.w || !d.h) return null;
        var c = scratchSized('t', d.w, d.h), x = c.getContext('2d');
        resetCtx(x, d.w, d.h);
        var f = adjustFilter(layer);
        if (f) x.filter = f;           // HSB first: the overlay colour stays EXACTLY the colour the painter picked
        x.drawImage(srcImg, 0, 0);
        x.filter = 'none';
        var a = co.opacity != null ? Number(co.opacity) : 0.5;
        a = a < 0 ? 0 : (a > 1 ? 1 : a);
        var color = co.color || '#ff3366';
        var bm = (co.blendMode && BLENDS[co.blendMode]) ? co.blendMode : 'source-over';
        if (bm === 'source-over') {
            // source-atop mixes the colour INTO the existing pixels and leaves their alpha untouched (edges stay clean)
            x.globalCompositeOperation = 'source-atop'; x.globalAlpha = a; x.fillStyle = color; x.fillRect(0, 0, d.w, d.h);
        } else {
            var oc = scratchSized('o', d.w, d.h), ox = oc.getContext('2d');
            resetCtx(ox, d.w, d.h);
            ox.drawImage(c, 0, 0);
            ox.globalCompositeOperation = 'source-in'; ox.fillStyle = color; ox.fillRect(0, 0, d.w, d.h);
            x.globalCompositeOperation = bm; x.globalAlpha = a; x.drawImage(oc, 0, 0);
        }
        x.globalAlpha = 1; x.globalCompositeOperation = 'source-over';
        return c;
    }
    var origDraw = window._drawLayerPixelContent;
    if (typeof origDraw === 'function' && !origDraw.__tlay) {
        var wd = function (ctx, layers, layerIndex, sourceOverride) {
            var layer = layers && layers[layerIndex];
            var fx = layer && layer.effects;
            if (off() || !fx || !fx.colorOverlay || !fx.colorOverlay.enabled || !layer.img) return origDraw.apply(this, arguments);
            var tint = null;
            try { tint = bakeOverlay(sourceOverride || layer.img, layer, scaleFx(fx, fxK(), ['colorOverlay']).colorOverlay); } catch (_e) { tint = null; }
            if (!tint) return origDraw.apply(this, arguments);
            stats.overlayBaked++;
            if (baked) baked.add(layer);
            var h = layer.adjHue, s = layer.adjSat, b = layer.adjBri;
            var hadAdj = !!(Number(h) || Number(s) || Number(b));
            var savedImg = layer.img;
            try {
                if (hadAdj) { layer.adjHue = 0; layer.adjSat = 0; layer.adjBri = 0; }   // already baked into `tint`
                if (sourceOverride) return origDraw.call(this, ctx, layers, layerIndex, tint);
                layer.img = tint;
                return origDraw.call(this, ctx, layers, layerIndex, null);
            } finally {
                layer.img = savedImg;
                if (hadAdj) { layer.adjHue = h; layer.adjSat = s; layer.adjBri = b; }
            }
        };
        wd.__tlay = true;
        window._drawLayerPixelContent = wd;
    }

    // ---------------------------------------------------------------- TL-02 real stroke band
    function ringStamp(x, src, r) {
        var rings = r > 4 ? [r, r * 0.5] : [r];
        for (var k = 0; k < rings.length; k++) {
            var rr = rings[k];
            var n = Math.max(8, Math.min(72, Math.ceil(rr * Math.PI / 1.5)));
            for (var i = 0; i < n; i++) {
                var a = (i / n) * 2 * Math.PI;
                x.drawImage(src, Math.cos(a) * rr, Math.sin(a) * rr);
            }
        }
    }
    function dilated(src, r, W, H) {
        var c = mk(W, H), x = c.getContext('2d');
        x.drawImage(src, 0, 0);
        ringStamp(x, src, r);
        return c;
    }
    // returns {canvas, dx, dy}: opaque-alpha band in the stroke colour, positioned in destination canvas coordinates
    function strokeBand(layer, st) {
        var d = dimsOf(layer.img);
        var x0 = layer.bbox ? Number(layer.bbox[0]) || 0 : 0, y0 = layer.bbox ? Number(layer.bbox[1]) || 0 : 0;
        var r = Math.max(1, Number(st.width) || 2);
        var pos = st.position === 'inside' || st.position === 'center' ? st.position : 'outside';
        var rOut = pos === 'outside' ? r : (pos === 'center' ? r / 2 : 0);
        var rIn = pos === 'inside' ? r : (pos === 'center' ? r / 2 : 0);
        var pad = Math.ceil(Math.max(rOut, rIn)) + 2;
        var W = d.w + pad * 2, H = d.h + pad * 2;
        var A = mk(W, H), ax = A.getContext('2d');
        ax.drawImage(layer.img, pad, pad, d.w, d.h);
        var D = rOut > 0 ? dilated(A, rOut, W, H) : A;
        var E = A;
        if (rIn > 0) {
            var N = mk(W, H), nx = N.getContext('2d');          // the empty space around/inside the shape
            nx.fillStyle = '#fff'; nx.fillRect(0, 0, W, H);
            nx.globalCompositeOperation = 'destination-out'; nx.drawImage(A, 0, 0);
            var ND = dilated(N, rIn, W, H);                    // the empty space grown INTO the shape
            E = mk(W, H); var ex = E.getContext('2d');
            ex.drawImage(A, 0, 0);
            ex.globalCompositeOperation = 'destination-out'; ex.drawImage(ND, 0, 0);   // eroded shape
        }
        var res = mk(W, H), rx = res.getContext('2d');
        rx.drawImage(D, 0, 0);
        rx.globalCompositeOperation = 'destination-out'; rx.drawImage(E, 0, 0);
        rx.globalCompositeOperation = 'source-in'; rx.fillStyle = st.color || '#ffffff'; rx.fillRect(0, 0, W, H);
        return { canvas: res, dx: x0 - pad, dy: y0 - pad };
    }

    // ---------------------------------------------------------------- TL-03 effects follow layer opacity + blend
    var tmp = null;
    function tmpFor(ctx) {
        var w = ctx.canvas.width, h = ctx.canvas.height;
        if (!tmp || tmp.width !== w || tmp.height !== h) tmp = mk(w, h);
        var x = tmp.getContext('2d');
        resetCtx(x, w, h);
        return tmp;
    }
    function blit(ctx, src, op, bm) {
        ctx.save();
        ctx.globalAlpha = op;
        ctx.globalCompositeOperation = bm;
        ctx.drawImage(src, 0, 0);
        ctx.restore();
    }
    function enabled(fx, k) { return !!(fx[k] && fx[k].enabled); }
    var FX_DEFAULT_OPACITY = { dropShadow: 0.75, outerGlow: 0.8, stroke: 1, colorOverlay: 0.5 };
    function scaleFx(fx, k, names) {
        var out = {};
        names.forEach(function (n) {
            if (!fx[n]) return;
            var c = {}; for (var p in fx[n]) c[p] = fx[n][p];
            if (k !== 1) { var o = (c.opacity != null ? Number(c.opacity) : FX_DEFAULT_OPACITY[n]) * k; c.opacity = o < 0 ? 0 : (o > 1 ? 1 : o); }
            out[n] = c;
        });
        return out;
    }
    var origFx = window.renderLayerEffects;
    if (typeof origFx === 'function' && !origFx.__tlay) {
        var wfx = function (ctx, layer, phase) {
            var fx = layer && layer.effects;
            if (off() || !fx || !layer.img || !ctx || !ctx.canvas) return origFx.apply(this, arguments);
            var d = dimsOf(layer.img);
            if (!d.w || !d.h) return;
            var op = layerOpacity(layer), bm = layerBlend(layer);
            var plain = op >= 0.999 && bm === 'source-over';
            var k = fxK();   // TL-12 global FX strength (the FX x button)
            if (phase === 'before') {
                if (baked) baked.delete(layer);
                if (!enabled(fx, 'dropShadow') && !enabled(fx, 'outerGlow')) return;
                var bl = layer;
                if (k !== 1) { bl = Object.create(layer); bl.effects = scaleFx(fx, k, ['dropShadow', 'outerGlow']); }
                if (plain) return origFx.call(this, ctx, bl, 'before');
                var t = tmpFor(ctx);
                origFx.call(this, t.getContext('2d'), bl, 'before');
                blit(ctx, t, op, bm);
                return;
            }
            if (phase !== 'after') return origFx.apply(this, arguments);
            var wasBaked = !!(baked && baked.has(layer));
            if (baked) baked.delete(layer);
            if (enabled(fx, 'stroke')) {
                try {
                    var band = strokeBand(layer, fx.stroke);
                    var so = (fx.stroke.opacity != null ? Number(fx.stroke.opacity) : 1) * k;
                    ctx.save();
                    ctx.globalAlpha = (so < 0 ? 0 : (so > 1 ? 1 : so)) * op;
                    ctx.globalCompositeOperation = bm;
                    ctx.drawImage(band.canvas, band.dx, band.dy);
                    ctx.restore();
                    stats.strokeDrawn++;
                } catch (_e) { }
            }
            if (!wasBaked && enabled(fx, 'colorOverlay')) {
                // layer pixels were drawn raw by the caller (Merge Down of the lower layer) -> legacy over-the-destination overlay
                var po = Object.create(layer); po.effects = scaleFx(fx, k, ['colorOverlay']);
                origFx.call(this, ctx, po, 'after');
            }
            if (enabled(fx, 'bevel')) {
                var pb = Object.create(layer); pb.effects = { bevel: fx.bevel };
                var bk = k > 1 ? 1 : k;
                if (plain && bk === 1) origFx.call(this, ctx, pb, 'after');
                else { var tb = tmpFor(ctx); origFx.call(this, tb.getContext('2d'), pb, 'after'); blit(ctx, tb, op * bk, bm); }
            }
        };
        wfx.__tlay = true;
        window.renderLayerEffects = wfx;
    }

    // ---------------------------------------------------------------- TL-04 export bakes effects
    function paintFxOn(l) {
        var fx = l && l.effects;
        return !!(fx && (enabled(fx, 'stroke') || enabled(fx, 'colorOverlay') || enabled(fx, 'dropShadow') || enabled(fx, 'outerGlow') || enabled(fx, 'bevel')));
    }
    function fxPad(l) {
        var fx = l.effects, pad = 0;
        if (enabled(fx, 'stroke') && fx.stroke.position !== 'inside') pad = Math.max(pad, Math.ceil((Number(fx.stroke.width) || 2) * (fx.stroke.position === 'center' ? 0.5 : 1)) + 2);
        if (enabled(fx, 'dropShadow')) pad = Math.max(pad, Math.ceil((Number(fx.dropShadow.distance) || 5) + (Number(fx.dropShadow.size) || 5) * 2) + 2);
        if (enabled(fx, 'outerGlow')) pad = Math.max(pad, Math.ceil((Number(fx.outerGlow.size) || 10) * 2 + (Number(fx.outerGlow.spread) || 0)) + 2);
        return Math.min(pad, 256);
    }
    var origExport = window.exportLayerAsPng;
    if (typeof origExport === 'function' && !origExport.__tlay) {
        var wex = function (layerId) {
            var l = (typeof _psdLayers !== 'undefined') ? _psdLayers.find(function (x) { return x.id === layerId; }) : null;
            if (off() || !l || !l.img || !paintFxOn(l)) return origExport.apply(this, arguments);
            try {
                var d = dimsOf(l.img), pad = fxPad(l);
                var out = mk(d.w + pad * 2, d.h + pad * 2), ctx = out.getContext('2d');
                var proxy = Object.create(l);
                proxy.bbox = [pad, pad, pad + d.w, pad + d.h];
                proxy.opacity = 255; proxy.blendMode = 'source-over'; proxy.clippingMask = false; proxy.visible = true;   // the file re-imports at 100% / Normal
                window.renderLayerEffects(ctx, proxy, 'before');
                window._drawLayerPixelContent(ctx, [proxy], 0, null);
                ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
                window.renderLayerEffects(ctx, proxy, 'after');
                var a = document.createElement('a');
                a.href = out.toDataURL('image/png');
                a.download = (l.name || 'layer').replace(/[^A-Za-z0-9 _-]+/g, '_').slice(0, 60) + '.png';
                a.click();
                stats.exportFx++;
                toast('Exported "' + (l.name || 'layer') + '" (' + out.width + '×' + out.height + ' PNG, effects baked)');
                return true;
            } catch (e) {
                toast('Layer export failed: ' + e.message, true);
                return false;
            }
        };
        wex.__tlay = true;
        window.exportLayerAsPng = wex;
    }

    // ---------------------------------------------------------------- TL-05 merge into a hidden lower layer
    var origMerge = window.mergeLayerDown;
    if (typeof origMerge === 'function' && !origMerge.__tlay) {
        var wmg = function (layerId) {
            if (!off() && typeof _psdLayers !== 'undefined') {
                var idx = _psdLayers.findIndex(function (l) { return l.id === layerId; });
                if (idx > 0) {
                    var up = _psdLayers[idx], lo = _psdLayers[idx - 1];
                    if (up && lo && up.img && lo.img && up.visible !== false && lo.visible === false) {
                        stats.mergeHiddenRefused++;
                        toast('"' + (lo.name || 'Layer') + '" is hidden — show it first to merge down into it', 'warn');
                        return;
                    }
                }
            }
            // [SPB-TLAY 2026-10-09 TL-06] Merge Down reset the surviving layer to Normal, so a Multiply / Overlay / Linear Dodge lower layer
            // changed the whole look of the car after the merge (lower Multiply (23,34,30) -> (32,96,192)). Photoshop keeps the lower
            // layer's blend mode; its opacity is already baked into the merged alpha (exact for every separable mode).
            var keepMode = null, keepId = null;
            if (!off() && typeof _psdLayers !== 'undefined') {
                var i2 = _psdLayers.findIndex(function (l) { return l.id === layerId; });
                var lo2 = i2 > 0 ? _psdLayers[i2 - 1] : null;
                var up2 = i2 > 0 ? _psdLayers[i2] : null;
                if (lo2 && up2 && up2.img && lo2.img && !up2.locked && !lo2.locked && lo2.blendMode && lo2.blendMode !== 'source-over' && lo2.blendMode !== 'pass-through') { keepMode = lo2.blendMode; keepId = lo2.id; }
            }
            var mres = origMerge.apply(this, arguments);
            if (keepMode) {
                var merged = _psdLayers.find(function (l) { return l.id === keepId; });
                var gone = !_psdLayers.some(function (l) { return l.id === layerId; });
                if (merged && gone && (merged.blendMode === 'source-over' || !merged.blendMode)) {
                    merged.blendMode = keepMode;
                    stats.mergeKeptMode = (stats.mergeKeptMode || 0) + 1;
                    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                    if (typeof renderLayerPanel === 'function') renderLayerPanel();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    var lbl = (window.SPBPcBlend && window.SPBPcBlend.MODES && window.SPBPcBlend.MODES[keepMode] && window.SPBPcBlend.MODES[keepMode].label) ||
                        String(keepMode).replace(/^color-/, '').replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
                    toast('Layers merged, kept the lower layer\'s ' + lbl + ' blend mode');
                }
            }
            return mres;
        };
        wmg.__tlay = true;
        window.mergeLayerDown = wmg;
    }

    // ---------------------------------------------------------------- TL-10 unique duplicate names
    function uniqueCopyName(newLayer, tag) {
        // tag = ' copy' or ' (mirror)'
        var base = String(newLayer.name || 'Layer');
        var re = tag === ' copy' ? / copy(?: (\d+))?$/ : / \(mirror(?: (\d+))?\)$/;
        var m = base.match(re);
        if (m) base = base.slice(0, m.index);
        var used = {};
        var maxN = 0;
        _psdLayers.forEach(function (l) {
            if (!l || l === newLayer) return;
            var nm = String(l.name || '');
            if (nm.indexOf(base) !== 0) return;
            var rest = nm.slice(base.length);
            var mm = rest.match(tag === ' copy' ? /^ copy(?: (\d+))?$/ : /^ \(mirror(?: (\d+))?\)$/);
            if (mm) { var n = mm[1] ? parseInt(mm[1], 10) : 1; if (n > maxN) maxN = n; used[n] = true; }
        });
        if (!maxN) return base + (tag === ' copy' ? ' copy' : ' (mirror)');
        var next = maxN + 1;
        return tag === ' copy' ? base + ' copy ' + next : base + ' (mirror ' + next + ')';
    }
    function wrapDup(name, tag) {
        var o = window[name];
        if (typeof o !== 'function' || o.__tlay) return;
        var w = function () {
            if (off() || typeof _psdLayers === 'undefined') return o.apply(this, arguments);
            var before = new Set(_psdLayers.map(function (l) { return l.id; }));
            var r = o.apply(this, arguments);
            try {
                var added = _psdLayers.filter(function (l) { return !before.has(l.id); });
                if (added.length === 1) {
                    var nl = added[0];
                    var want = uniqueCopyName(nl, tag);
                    if (want !== nl.name) {
                        nl.name = want;
                        if (typeof renderLayerPanel === 'function') renderLayerPanel();
                    }
                }
            } catch (_e) { }
            return r;
        };
        w.__tlay = true;
        window[name] = w;
    }
    wrapDup('duplicateLayer', ' copy');
    wrapDup('duplicateLayerWithOffset', ' copy');
    wrapDup('mirrorCloneLayer', ' (mirror)');

    // ---------------------------------------------------------------- TL-11 PAN / FIT really move the view
    // paint-booth-layer-flow.js panToLayer() looks for zoomToBounds / fitCanvasToBbox / panCanvasTo / centerCanvasOn; none existed, so
    // the PAN and FIT buttons (and the right-click "Pan to layer" / "Fit to layer") only showed a "Pan to bbox 778, 1223" toast.
    // Defining two of those hooks fixes all four entry points without touching the flow module.
    function scrollerOf() {
        try { if (typeof getScrollContainer === 'function') return getScrollContainer(); } catch (_e) { }
        return document.getElementById('canvasViewport');
    }
    function centreViewOn(cx, cy) {
        var sc = scrollerOf(), pc = document.getElementById('paintCanvas');
        if (!sc || !pc || !pc.width) return false;
        var pr = pc.getBoundingClientRect(), sr = sc.getBoundingClientRect();
        var z = pr.width / pc.width;
        var left = (pr.left - sr.left) + sc.scrollLeft + cx * z - sc.clientWidth / 2;
        var top = (pr.top - sr.top) + sc.scrollTop + cy * z - sc.clientHeight / 2;
        sc.scrollLeft = Math.max(0, left); sc.scrollTop = Math.max(0, top);
        return true;
    }
    function legacyPanFallback(cx, cy, fit) {
        var canvas = document.getElementById('paintCanvas');
        if (canvas && canvas.scrollIntoView) canvas.scrollIntoView({ behavior: 'smooth', block: 'center' });
        toast((fit ? 'Fit to' : 'Pan to') + ' bbox ' + Math.round(cx) + ', ' + Math.round(cy));
    }
    if (typeof window.zoomToBounds !== 'function') {
        window.zoomToBounds = function (bbox) {
            var pc = document.getElementById('paintCanvas'), sc = scrollerOf();
            var b = Array.isArray(bbox) ? bbox : [0, 0, pc ? pc.width : 2048, pc ? pc.height : 2048];
            var cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
            if (off() || !pc || !sc || typeof applyZoom !== 'function') { legacyPanFallback(cx, cy, true); return false; }
            var bw = Math.max(1, Math.min(b[2], pc.width) - Math.max(0, b[0])), bh = Math.max(1, Math.min(b[3], pc.height) - Math.max(0, b[1]));
            var z = Math.min((sc.clientWidth - 40) / bw, (sc.clientHeight - 40) / bh, 8);
            currentZoom = Math.max(0.1, z);
            applyZoom();
            centreViewOn(cx, cy);
            setTimeout(function () { centreViewOn(cx, cy); }, 60);
            toast('Fit to layer (' + Math.round(bw) + '×' + Math.round(bh) + ' px) — Fit button above returns to the whole car');
            return true;
        };
    }
    if (typeof window.panCanvasTo !== 'function') {
        window.panCanvasTo = function (cx, cy) {
            var pc = document.getElementById('paintCanvas'), sc = scrollerOf();
            if (off() || !pc || !sc || typeof applyZoom !== 'function') { legacyPanFallback(cx, cy, false); return false; }
            // At FIT the whole car is already in view, so a pure pan would visibly do nothing: step in to 100% first.
            var fitZ = window.__spbFitZoom || 0;
            var atFit = (pc.getBoundingClientRect().width / pc.width) <= Math.max(fitZ, 0.0001) * 1.05 || (sc.scrollWidth <= sc.clientWidth + 2 && sc.scrollHeight <= sc.clientHeight + 2);
            if (atFit) { currentZoom = 1; applyZoom(); }
            centreViewOn(cx, cy);
            setTimeout(function () { centreViewOn(cx, cy); }, 60);
            toast('Centred on the layer' + (atFit ? ' at 100%' : ''));
            return true;
        };
    }

    // ---------------------------------------------------------------- TL-12 FX x is real (and shows its value)
    function fxK() {
        try { var F = window.spbLayerFlow; var k = F && F.getEffectIntensity ? Number(F.getEffectIntensity()) : 1; return (k >= 0 && k <= 2) ? k : 1; } catch (_e) { return 1; }
    }
    function paintFxLabel() {
        if (off()) return;
        var k = fxK();
        var btns = document.querySelectorAll('#layerPanelContent button[title^="Cycle the global FX intensity"]');
        for (var i = 0; i < btns.length; i++) btns[i].textContent = k === 1 ? 'FX ×' : 'FX × ' + k.toFixed(2);
    }
    var flowWrapped = false;
    function wrapFlow() {
        var F = window.spbLayerFlow;
        if (flowWrapped || !F || typeof F.setEffectIntensity !== 'function') return;
        flowWrapped = true;
        // the persisted multiplier would silently change every render of a later session -> always start at 1.00
        try { if (F.getEffectIntensity() !== 1) F.setEffectIntensity(1.0); } catch (_e) { }
        var oSet = F.setEffectIntensity;
        F.setEffectIntensity = function (v) {
            var r = oSet.apply(this, arguments);
            if (!off()) { paintFxLabel(); toast('Layer FX strength ×' + fxK().toFixed(2) + ' (Shift-click FX × = back to 1.00)'); }
            return r;
        };
    }

    // ---------------------------------------------------------------- TL-09 opacity number box
    document.addEventListener('input', function (e) {
        if (off()) return;
        var t = e.target;
        if (t && t.matches && t.matches('[data-layer-opacity-input]') && String(t.value).trim() === '') e.stopImmediatePropagation();
    }, true);
    document.addEventListener('focusout', function (e) {
        if (off()) return;
        var t = e.target;
        if (!t || !t.matches || !t.matches('[data-layer-opacity-input]') || String(t.value).trim() !== '') return;
        try {
            var id = t.getAttribute('data-layer-opacity-input');
            var L = _psdLayers.find(function (l) { return String(l.id) === String(id); });
            if (L) t.value = String(Math.round(((L.opacity != null ? L.opacity : 255) / 255) * 100));
        } catch (_e) { }
    }, true);

    window.SPBTLay = { version: 'tlay-1', off: off, stats: stats, fp: zoneFpNow, strokeBand: strokeBand, bakeOverlay: bakeOverlay };
})();
