/* [SPB-TLAY2 2026-10-10] L2-3 (TL-08) -- the layer card's Hue / Sat / Bright sliders use the PhotoCraft Hue/Saturation math.
 *
 * BEFORE: the three card sliders were a CSS canvas filter (hue-rotate + saturate + brightness). Preview and RENDER agreed (both go through
 *   _drawLayerPixelContent), but the colours were NOT what Photoshop / the Adjust -> Hue/Saturation layer give: CSS hue-rotate is a linear RGB matrix
 *   that darkens and muddies (a red 200,40,40 at Hue +90 became a dark green 34,123,0), and "Sat" was a matrix too.
 * NOW: Hue and Sat go through SPBPcAdjust's hueSat (HSL, the same code the Adjust layer runs; GPU first, CPU fallback). Bright keeps the exact linear gain
 *   the CSS filter used (so a Bright-only layer is bit-identical to before: this module hands those back to the old path).
 * Still non-destructive (the layer pixels never change; the baked copy exists only while drawing) and undoable (same gesture / undo as before).
 *
 * How: wraps window._drawLayerPixelContent (the one draw path shared by recompositeFromLayers and buildLivePaintCompositeCanvas, so preview and the
 *   RENDER payload cannot disagree). For a layer with Hue/Sat set it draws a baked copy with the CSS adjust zeroed. Other places that draw a layer
 *   by hand (Export PNG, Merge Down, thumbnails, PhotoCraft hand-off) call SPBTlay2Hsb.baked(layer) so they match.
 * Kill switches: window.SPB_TLAY2_HSB_OFF = true (this only) or SPB_TLAY2_OFF = true (whole lane) -> the old CSS-filter behaviour, exactly.
 */
(function () {
    'use strict';
    if (window.SPBTlay2Hsb) return;

    var stats = { baked: 0, gpu: 0, cpu: 0, fallback: 0, lastMs: 0, lastPath: '' };
    function off() { return window.SPB_TLAY2_OFF === true || window.SPB_TLAY2_HSB_OFF === true; }
    function num(v) { return Number(v) || 0; }
    function mkc(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
    function dimsOf(src) { return { w: src.naturalWidth || src.width || 0, h: src.naturalHeight || src.height || 0 }; }
    function active(layer) { return !!layer && !off() && (num(layer.adjHue) !== 0 || num(layer.adjSat) !== 0); }

    // returns a NEW canvas with the layer's Hue/Sat/Bright applied to `src` (default layer.img), or null = "use the legacy CSS filter"
    function bake(layer, src) {
        if (!active(layer)) return null;
        var P = window.SPBPcAdjust;
        if (!P || typeof P.process !== 'function' || (typeof P.off === 'function' && P.off())) return null;
        src = src || layer.img;
        if (!src) return null;
        var d = dimsOf(src);
        if (!d.w || !d.h) return null;
        var t0 = performance.now(), params = { hue: num(layer.adjHue), saturation: num(layer.adjSat), lightness: 0 }, out = null, path = '';
        var cv = src;
        if (!(typeof HTMLCanvasElement !== 'undefined' && src instanceof HTMLCanvasElement)) { cv = mkc(d.w, d.h); cv.getContext('2d').drawImage(src, 0, 0); }
        if (typeof P.processGpu === 'function') {
            try { out = P.processGpu('hueSat', params, cv, 1); if (out) path = 'gpu'; } catch (e) { out = null; }
        }
        if (!out) {
            try {
                out = mkc(d.w, d.h);
                var g = out.getContext('2d', { willReadFrequently: true });
                g.drawImage(cv, 0, 0);
                var id = g.getImageData(0, 0, d.w, d.h);
                P.process('hueSat', params, id.data, null, 1);
                g.putImageData(id, 0, 0);
                path = 'cpu';
            } catch (e) { return null; }   // tainted / too big: fall back to the CSS filter rather than draw nothing
        }
        var b = num(layer.adjBri);
        if (b) {   // the Bright slider keeps its exact CSS meaning (linear gain, 100 + b %)
            var o2 = mkc(d.w, d.h), g2 = o2.getContext('2d');
            g2.filter = 'brightness(' + Math.max(0, 100 + b) + '%)';
            g2.drawImage(out, 0, 0);
            g2.filter = 'none';
            out = o2;
        }
        stats.baked++; stats[path]++; stats.lastMs = performance.now() - t0; stats.lastPath = path;
        return out;
    }

    function baked(layer, src) { try { return bake(layer, src); } catch (e) { return null; } }

    function install() {
        var orig = window._drawLayerPixelContent;
        if (typeof orig !== 'function' || orig.__tlay2hsb) return false;
        var w = function (ctx, layers, layerIndex, sourceOverride) {
            var layer = layers && layers[layerIndex];
            if (!active(layer) || !(sourceOverride || layer.img)) return orig.apply(this, arguments);
            var b = baked(layer, sourceOverride || layer.img);
            if (!b) { stats.fallback++; return orig.apply(this, arguments); }
            var h = layer.adjHue, s = layer.adjSat, br = layer.adjBri, savedImg = layer.img;
            try {
                layer.adjHue = 0; layer.adjSat = 0; layer.adjBri = 0;   // already baked into `b`
                if (sourceOverride) return orig.call(this, ctx, layers, layerIndex, b);
                layer.img = b;
                return orig.call(this, ctx, layers, layerIndex, null);
            } finally {
                layer.img = savedImg;
                layer.adjHue = h; layer.adjSat = s; layer.adjBri = br;
            }
        };
        w.__tlay2hsb = true; w.__orig = orig;
        window._drawLayerPixelContent = w;
        return true;
    }

    function uninstall() {
        var cur = window._drawLayerPixelContent;
        if (cur && cur.__tlay2hsb && cur.__orig) window._drawLayerPixelContent = cur.__orig;
    }

    window.SPBTlay2Hsb = { version: 'tlay2-3', bake: bake, baked: baked, active: active, install: install, uninstall: uninstall, stats: stats };
    install();
})();
