/* Photoshop-parity blend modes wired into the SPB layer stack (ticket TL-14).
 * Maths: pc-blend.js, ported from PhotoCraft crates/color/src/blend.rs - (c) 2026 ArtCraft Team and the PhotoCraft
 * contributors, MIT OR Apache-2.0 (see THIRD_PARTY_NOTICES.md). Modified: JavaScript for Shokker Paint Booth.
 * Lane TOOLS-LAYERS, 2026-10-09.
 *
 *  - 11 Photoshop modes Canvas2D does not have (Linear Burn, Linear Dodge (Add), Vivid/Linear/Pin Light, Hard Mix,
 *    Darker/Lighter Color, Subtract, Divide, Dissolve) are added to the Blend dropdown and composited with
 *    SPBPcBlend (bit-exact to PhotoCraft's flatten of the same layers, see layers/pcsrc/blend_key.py).
 *  - 4 native modes whose Skia maths measurably differs from Photoshop (Soft Light up to 12 levels, Color Dodge/Burn
 *    up to 63, Hue up to 177 on neutral backdrops) are routed through the same exact compositor.
 *  - PSD import used to turn every one of the new modes into Normal (a Linear Dodge glow vanished); they now map.
 * Kill switch: window.SPB_TLAY_OFF = true (or localStorage SPB_TLAY_OFF=1) restores the previous behaviour.
 */
(function () {
    'use strict';
    var B = window.SPBPcBlend;
    if (!B || window.SPBPcLayers) return;
    function off() { return window.SPB_TLAY_OFF === true; }
    try { if (window.localStorage && window.localStorage.getItem('SPB_TLAY_OFF') === '1') window.SPB_TLAY_OFF = true; } catch (_e) {}

    var stats = { customDraws: 0, importMapped: 0, lastMs: 0 };
    var undoers = [];   // dev/test: SPBPcLayers.uninstall() puts every original back so the file can be re-injected without a reboot
    function mk(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
    var pool = {};
    function scratch(w, h) {
        var k = w + 'x' + h, c = pool[k];
        if (!c) {
            var keys = Object.keys(pool);
            if (keys.length > 3) delete pool[keys[0]];
            c = pool[k] = mk(w, h);
            c.__ctx = c.getContext('2d', { willReadFrequently: true });
        }
        return c;
    }
    function newModeIds() { return B.ORDER.slice(); }
    function isNewMode(id) { return B.has(id) && !B.isOverride(id); }

    // ------------------------------------------------------------------ [SPB-TLAY 2026-10-09 TL-14] custom blend in the draw path
    var prevDraw = window._drawLayerPixelContent;
    if (typeof prevDraw === 'function' && !prevDraw.__pcl) {
        var wdraw = function (ctx, layers, idx, sourceOverride) {
            var layer = layers && layers[idx];
            if (off() || !layer || !layer.blendMode || !B.has(layer.blendMode) || !(sourceOverride || layer.img)) return prevDraw.apply(this, arguments);
            var T = ctx.getTransform ? ctx.getTransform() : null;
            if (T && (T.a !== 1 || T.d !== 1 || T.b !== 0 || T.c !== 0)) return prevDraw.apply(this, arguments);   // scaled target: leave to Canvas2D
            var t0 = performance.now();
            var tx = T ? T.e : 0, ty = T ? T.f : 0;
            var cv = ctx.canvas, cw = cv.width, ch = cv.height;
            var bb = layer.bbox, ix = sourceOverride ? 0 : (bb ? Number(bb[0]) || 0 : 0), iy = sourceOverride ? 0 : (bb ? Number(bb[1]) || 0 : 0);
            var src = sourceOverride || layer.img;
            var sw = Number(src.naturalWidth || src.width) || 0, sh = Number(src.naturalHeight || src.height) || 0;
            var x0 = Math.max(0, Math.floor(ix + tx)), y0 = Math.max(0, Math.floor(iy + ty));
            var x1 = Math.min(cw, Math.ceil(ix + tx + sw)), y1 = Math.min(ch, Math.ceil(iy + ty + sh));
            if (x1 <= x0 || y1 <= y0) return true;   // entirely off-canvas: nothing to blend
            var w = x1 - x0, h = y1 - y0;
            // 1. the layer's own pixels (clipping, HSB, colour overlay all handled by the previous chain), plain Normal at 100%
            var sc = scratch(cw, ch), sx = sc.__ctx;
            sx.setTransform(1, 0, 0, 1, 0, 0); sx.globalAlpha = 1; sx.globalCompositeOperation = 'source-over'; sx.filter = 'none';
            sx.clearRect(0, 0, cw, ch);
            if (T) sx.setTransform(T);
            var proxy = Object.assign({}, layer, { blendMode: 'source-over', opacity: 255 });
            var arr = layers.slice(); arr[idx] = proxy;
            var drew = prevDraw.call(this, sx, arr, idx, sourceOverride);
            sx.setTransform(1, 0, 0, 1, 0, 0);
            if (drew === false) return false;
            var s = sx.getImageData(x0, y0, w, h);
            // 2. backdrop under the layer, blended in place with the Photoshop maths, written back exactly
            var bd = ctx.getImageData(x0, y0, w, h);
            var op = (layer.opacity != null ? layer.opacity : 255) / 255;
            B.compositeRegion(bd.data, s.data, w * h, layer.blendMode, op, w, x0 - tx, y0 - ty);
            ctx.putImageData(bd, x0, y0);
            stats.customDraws++; stats.lastMs = performance.now() - t0;
            return true;
        };
        wdraw.__pcl = true;
        window._drawLayerPixelContent = wdraw;
        undoers.push(function () { if (window._drawLayerPixelContent === wdraw) window._drawLayerPixelContent = prevDraw; });
    }

    // ------------------------------------------------------------------ Blend dropdown + setLayerBlendMode accepts the new ids
    var prevSet = window.setLayerBlendMode;
    if (typeof prevSet === 'function' && !prevSet.__pcl) {
        var wset = function (layerId, mode, options) {
            if (off() || !isNewMode(mode)) return prevSet.apply(this, arguments);
            var layer = (window._psdLayers || []).find(function (l) { return l.id === layerId; });
            if (!layer) return false;
            var cur = layer.blendMode || 'source-over';
            if (cur === mode) { if (typeof window._syncLayerBlendModeControls === 'function') window._syncLayerBlendModeControls(layerId, cur); return true; }
            if (layer.locked) {
                if (typeof window._syncLayerBlendModeControls === 'function') window._syncLayerBlendModeControls(layerId, cur);
                if (typeof window.showToast === 'function') window.showToast('Layer is locked — unlock to change blend mode', true);
                return false;
            }
            window._pushLayerStackUndo('blend → ' + B.MODES[mode].label);
            layer.blendMode = mode;
            if (typeof window._syncLayerBlendModeControls === 'function') window._syncLayerBlendModeControls(layerId, mode);
            window.recompositeFromLayers();
            if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
            if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
            return true;
        };
        wset.__pcl = true;
        window.setLayerBlendMode = wset;
        undoers.push(function () { if (window.setLayerBlendMode === wset) window.setLayerBlendMode = prevSet; });
    }
    function decorateBlendSelects() {
        if (off()) return;
        var panel = document.getElementById('layerPanelContent');
        if (!panel) return;
        var sels = panel.querySelectorAll('select[data-layer-blend-control]');
        for (var i = 0; i < sels.length; i++) {
            var sel = sels[i];
            if (sel.querySelector('optgroup[data-pcl]')) continue;
            var g = document.createElement('optgroup'); g.label = 'Photoshop modes'; g.setAttribute('data-pcl', '1');
            var id = sel.getAttribute('data-layer-blend-control');
            var layer = (window._psdLayers || []).find(function (l) { return l.id === id; });
            var curMode = layer && layer.blendMode;
            newModeIds().forEach(function (m) {
                var o = document.createElement('option'); o.value = m; o.textContent = B.MODES[m].label;
                if (curMode === m) o.selected = true;
                g.appendChild(o);
            });
            sel.appendChild(g);
        }
    }
    var prevPanel = window.renderLayerPanel;
    if (typeof prevPanel === 'function' && !prevPanel.__pcl) {
        var wpanel = function () {
            var r = prevPanel.apply(this, arguments);
            try { decorateBlendSelects(); } catch (_e) {}
            return r;
        };
        wpanel.__pcl = true;
        // keep the TL wrapper's own marks so later wrappers (and our idempotence checks) still see them
        for (var k in prevPanel) { try { if (Object.prototype.hasOwnProperty.call(prevPanel, k)) wpanel[k] = prevPanel[k]; } catch (_e2) {} }
        window.renderLayerPanel = wpanel;
        undoers.push(function () { if (window.renderLayerPanel === wpanel) window.renderLayerPanel = prevPanel; });
    }

    // ------------------------------------------------------------------ PSD import: map the new modes instead of downgrading to Normal
    function walkRaw(nodes, prefix, out) {
        (Array.isArray(nodes) ? nodes : []).forEach(function (node, index) {
            if (!node) return;
            var path = prefix.concat(index);
            if (Array.isArray(node.children)) { walkRaw(node.children, path, out); return; }
            if (!node.has_pixels) return;
            var key = String(node.layer_key != null ? node.layer_key : path.join('.'));
            var id = B.fromPsdKey(node.blend_mode);
            if (id && isNewMode(id)) out[key] = { id: id, key: String(node.blend_mode) };
        });
    }
    function wrapImport() {
        var api = window.SPBPSDImportSafety;
        if (!api || typeof api.flattenLayerTree !== 'function') return false;
        if (api.flattenLayerTree.__pcl) return true;
        var orig = api.flattenLayerTree;
        var w = function (tree, size) {
            var res = orig.apply(this, arguments);
            if (off() || !Array.isArray(res)) return res;
            try {
                var map = {}; walkRaw(tree, [], map);
                var hit = 0;
                res.forEach(function (l) {
                    var m = map[l.rasterKey];
                    if (m && (!l.blendMode || l.blendMode === 'source-over')) { l.blendMode = m.id; hit++; }
                });
                if (hit && Array.isArray(res.blendModeDowngrades)) {
                    res.blendModeDowngrades = res.blendModeDowngrades.filter(function (s) {
                        var mm = /\(([^)]*)\)\s*$/.exec(String(s));
                        return !(mm && B.fromPsdKey(mm[1]) && isNewMode(B.fromPsdKey(mm[1])));
                    });
                }
                stats.importMapped += hit;
            } catch (_e) {}
            return res;
        };
        w.__pcl = true;
        // the module returns a frozen object, so publish a new frozen copy that carries the wrapped function
        var copy = Object.assign({}, api, { flattenLayerTree: w });
        try { window.SPBPSDImportSafety = Object.freeze(copy); } catch (_e) { return false; }
        undoers.push(function () { if (window.SPBPSDImportSafety && window.SPBPSDImportSafety.flattenLayerTree === w) window.SPBPSDImportSafety = api; });
        return true;
    }
    if (!wrapImport()) { var tries = 0, iv = setInterval(function () { if (wrapImport() || ++tries > 40) clearInterval(iv); }, 500); }

    window.SPBPcLayers = { version: 'pcl-1', uninstall: function () { undoers.splice(0).forEach(function (f) { try { f(); } catch (_e) {} }); delete window.SPBPcLayers; }, stats: stats, off: off, newModeIds: newModeIds, decorateBlendSelects: decorateBlendSelects, scratch: scratch };
})();
