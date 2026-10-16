/* [STROKE-HL 2026-10-12] Live stroke highlight.
 * Owner 2026-10-12: "when I try to color in an area using the brush in the SOURCE BOX it should be coloring it a highlighted color
 * (which could be changed) at the exact same time so you can see where you are drawing/painting."
 *
 * What it is: ONE display-only overlay canvas (#strokeHlCanvas) stacked above #paintCanvas/#regionCanvas inside #canvasInner.
 * While the layer brush paints, js/canvas/pc-stroke.js writes the brush FOOTPRINT coverage (stroke coverage x selection, opacity ignored)
 * into a persistent Uint8ClampedArray alpha plane (o.hlOut) dab by dab; after each dab flush(rect) paints only that dab's rect on the overlay
 * (putImageData of the small rect - never a full 2048x2048 pass per pointermove). The overlay holds OPAQUE highlight colour with
 * coverage in its alpha channel and the element's CSS opacity (0.45) does the see-through, so overlapping dabs never stack darker.
 *
 * What it must never do: touch layer pixels, the composite, undo, renders or saved files. The overlay is a DOM sibling only - nothing in the
 * paint/render/export path reads it. It stays while the Brush tool stays active on the same layer and clears on tool change, layer change,
 * undo/redo, or the small "x" button.
 *
 * Kill switch: window.SPB_STROKE_HL_OFF = true (no overlay, no UI, no cost).  Prefs: localStorage spb_stroke_hl ('1'/'0', default on),
 * spb_stroke_hl_color (default #ff2bd6).
 */
(function (root) {
    'use strict';
    var doc = root.document;
    if (!doc) return;
    var LS_ON = 'spb_stroke_hl', LS_COL = 'spb_stroke_hl_color', DEF_COL = '#ff2bd6', CSS_ALPHA = 0.45;

    function lsGet(k) { try { return root.localStorage.getItem(k); } catch (_) { return null; } }
    function lsSet(k, v) { try { root.localStorage.setItem(k, v); } catch (_) {} }
    function validHex(h) { return typeof h === 'string' && /^#[0-9a-fA-F]{6}$/.test(h); }

    var st = {
        on: lsGet(LS_ON) !== '0',
        color: validHex(lsGet(LS_COL)) ? lsGet(LS_COL).toLowerCase() : DEF_COL,
        ov: null, ctx: null, buf: null, W: 0, H: 0, layerId: null,
        hasPaint: false, bx0: 0, by0: 0, bx1: 0, by1: 0,   // dirty bounds of everything drawn since the last clear
        tick: null, mo: null, ui: null, uiKey: '', dabs: 0
    };

    function off() { return !!root.SPB_STROKE_HL_OFF; }
    function enabled() { return !off() && st.on; }
    function mode() { try { return root.canvasMode; } catch (_) { return ''; } }
    function layerMode() { try { return typeof root.isLayerToolbarMode === 'function' && root.isLayerToolbarMode(); } catch (_) { return false; } }
    function rgbOf(hex) { return [parseInt(hex.slice(1, 3), 16) || 0, parseInt(hex.slice(3, 5), 16) || 0, parseInt(hex.slice(5, 7), 16) || 0]; }

    // ---- overlay canvas -----------------------------------------------------------------------------------------------------
    function syncLayout() {
        var pc = doc.getElementById('paintCanvas');
        if (!pc || !st.ov) return;
        var w = pc.style.width, h = pc.style.height;
        if (w && st.ov.style.width !== w) st.ov.style.width = w;
        if (h && st.ov.style.height !== h) st.ov.style.height = h;
    }
    function makeOverlay() {
        if (st.ov && st.ov.parentNode) return true;
        var pc = doc.getElementById('paintCanvas');
        if (!pc || !pc.parentNode) return false;
        var ov = st.ov || doc.createElement('canvas');
        ov.id = 'strokeHlCanvas';
        ov.setAttribute('aria-hidden', 'true');
        ov.setAttribute('style', 'position:absolute;top:0;left:0;display:none;pointer-events:none;z-index:3;opacity:' + CSS_ALPHA + ';');
        var region = doc.getElementById('regionCanvas');
        if (region && region.parentNode === pc.parentNode) pc.parentNode.insertBefore(ov, region.nextSibling);
        else pc.parentNode.insertBefore(ov, pc.nextSibling);
        st.ov = ov;
        st.ctx = ov.getContext('2d');
        if (!st.mo && typeof root.MutationObserver === 'function') {
            st.mo = new root.MutationObserver(syncLayout);
            st.mo.observe(pc, { attributes: true, attributeFilter: ['style'] });
        }
        syncLayout();
        return true;
    }
    function ensure(layerId, w, h) {
        if (!makeOverlay()) return false;
        if (st.W !== w || st.H !== h) {
            st.W = w; st.H = h;
            st.buf = new Uint8ClampedArray(w * h);
            st.ov.width = w; st.ov.height = h;   // also clears the overlay
            st.ctx = st.ov.getContext('2d');
            st.hasPaint = false;
            syncLayout();
        } else if (st.layerId !== layerId && st.hasPaint) {
            clear('layer');
        }
        st.layerId = layerId;
        return true;
    }

    // ---- public: called by paint-booth-3-canvas.js while the layer brush paints --------------------------------------------
    /** alpha plane for pc-stroke.js paintDab({hlOut}) or null when the highlight is off / not the brush tool */
    function bufferFor(layerId, w, h) {
        if (!enabled() || mode() !== 'brush') return null;
        return ensure(layerId, w, h) ? st.buf : null;
    }
    /** paint ONLY this dab's rect from the alpha plane to the overlay */
    function flush(rect) {
        if (!rect || !st.ctx || !st.buf) return;
        var x0 = Math.max(0, rect.x | 0), y0 = Math.max(0, rect.y | 0);
        var x1 = Math.min(st.W, x0 + (rect.width | 0)), y1 = Math.min(st.H, y0 + (rect.height | 0));
        var w = x1 - x0, h = y1 - y0;
        if (w <= 0 || h <= 0) return;
        var img = st.ctx.createImageData(w, h), d = img.data, b = st.buf, W = st.W, c = rgbOf(st.color), p = 0;
        for (var yy = 0; yy < h; yy++) {
            var gi = (y0 + yy) * W + x0;
            for (var xx = 0; xx < w; xx++, gi++, p += 4) {
                var a = b[gi];
                if (a) { d[p] = c[0]; d[p + 1] = c[1]; d[p + 2] = c[2]; d[p + 3] = a; }
            }
        }
        st.ctx.putImageData(img, x0, y0);
        if (!st.hasPaint) { st.hasPaint = true; st.bx0 = x0; st.by0 = y0; st.bx1 = x1; st.by1 = y1; }
        else { if (x0 < st.bx0) st.bx0 = x0; if (y0 < st.by0) st.by0 = y0; if (x1 > st.bx1) st.bx1 = x1; if (y1 > st.by1) st.by1 = y1; }
        st.dabs++;
        if (st.ov.style.display !== 'block') { syncLayout(); st.ov.style.display = 'block'; }
        startTick();
    }
    /** fallback for the legacy (non-coverage-buffer) dab paths: a soft disc into the plane, then the same flush */
    function circleDab(layerId, w, h, x, y, radius) {
        var b = bufferFor(layerId, w, h);
        if (!b) return;
        var r = Math.max(0.5, +radius || 1), cx = x + 0.5, cy = y + 0.5;
        var x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        var x1 = Math.min(w, Math.ceil(cx + r + 1)), y1 = Math.min(h, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return;
        for (var yy = y0; yy < y1; yy++) {
            var dy = yy + 0.5 - cy;
            for (var xx = x0; xx < x1; xx++) {
                var dx = xx + 0.5 - cx, e = r + 0.5 - Math.sqrt(dx * dx + dy * dy);
                if (e <= 0) continue;
                var a = ((e > 1 ? 1 : e) * 255 + 0.5) | 0, gi = yy * w + xx;
                if (a > b[gi]) b[gi] = a;
            }
        }
        flush({ x: x0, y: y0, width: x1 - x0, height: y1 - y0 });
    }
    function clear(why) {
        if (st.hasPaint && st.buf && st.ctx) {
            var W = st.W;
            for (var y = st.by0; y < st.by1; y++) st.buf.fill(0, y * W + st.bx0, y * W + st.bx1);
            st.ctx.clearRect(st.bx0, st.by0, st.bx1 - st.bx0, st.by1 - st.by0);
        }
        st.hasPaint = false;
        if (st.ov) st.ov.style.display = 'none';
        if (st.tick) { root.clearInterval(st.tick); st.tick = null; }
        st.lastClear = why || '';
        syncUi();
    }
    function startTick() {
        if (st.tick) return;
        // cheap watchdog only while a highlight is on screen: tool change / layer change from ANY code path clears it
        st.tick = root.setInterval(function () {
            if (!st.hasPaint) { root.clearInterval(st.tick); st.tick = null; return; }
            if (off() || !st.on || mode() !== 'brush' || root._selectedLayerId !== st.layerId) clear('tick');
        }, 150);
    }
    function onTool(m) { if (st.hasPaint && m !== 'brush') clear('tool'); syncUi(); }

    // ---- prefs ---------------------------------------------------------------------------------------------------------------
    function setOn(v) {
        st.on = !!v; lsSet(LS_ON, st.on ? '1' : '0');
        if (!st.on) clear('off');
        syncUi();
    }
    function setColor(hex) {
        if (!validHex(hex)) return false;
        st.color = hex.toLowerCase(); lsSet(LS_COL, st.color);
        if (st.hasPaint && st.ctx) {   // recolour in place: keep the coverage alpha, swap the colour (no per-pixel loop)
            st.ctx.save();
            st.ctx.globalCompositeOperation = 'source-in';
            st.ctx.fillStyle = st.color;
            st.ctx.fillRect(st.bx0, st.by0, st.bx1 - st.bx0, st.by1 - st.by0);
            st.ctx.restore();
        }
        syncUi();
        return true;
    }

    // ---- UI: compact "Highlight [x] [colour] [clear]" in the layer-brush options (static markup in paint-booth-v2.html) --------
    function grabUi() {
        if (st.ui) return st.ui;
        var wrap = doc.getElementById('strokeHlLabel');
        if (!wrap) return null;
        var ui = { wrap: wrap, cb: doc.getElementById('strokeHlToggle'), col: doc.getElementById('strokeHlColor'), clr: doc.getElementById('strokeHlClear') };
        if (!ui.cb || !ui.col || !ui.clr) return null;
        ui.cb.addEventListener('change', function () { setOn(ui.cb.checked); });
        ui.col.addEventListener('input', function () { setColor(ui.col.value); });
        ui.clr.addEventListener('click', function (e) { e.preventDefault(); clear('button'); });
        st.ui = ui;
        return ui;
    }
    function syncUi() {
        var ui = grabUi();
        if (!ui) return;
        var show = !off() && mode() === 'brush' && layerMode();
        var key = (show ? '1' : '0') + (st.on ? '1' : '0') + st.color + (st.hasPaint ? '1' : '0');
        if (key === st.uiKey) return;
        st.uiKey = key;
        ui.wrap.style.display = show ? 'inline-flex' : 'none';
        if (ui.cb.checked !== st.on) ui.cb.checked = st.on;
        if (ui.col.value !== st.color) ui.col.value = st.color;
        ui.col.disabled = !st.on;
        ui.clr.disabled = !st.hasPaint;
        ui.clr.style.opacity = st.hasPaint ? '1' : '0.4';
    }

    // undo/redo repaint the layer, so the footprint of the undone stroke would lie about the pixels: clear with them
    function wrapUndo(name) {
        var f = root[name];
        if (typeof f !== 'function' || f.__spbHl) return;
        var w = function () { try { if (st.hasPaint) clear(name); } catch (_) {} return f.apply(this, arguments); };
        w.__spbHl = true;
        root[name] = w;
    }
    function boot() {
        if (off()) return;
        grabUi(); syncUi();
        wrapUndo('undoLayerEdit'); wrapUndo('redoLayerEdit');
        root.setInterval(syncUi, 500);   // mode/layer-mode visibility safety net (a style-key compare only)
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot();

    root.SPBStrokeHL = {
        enabled: enabled, bufferFor: bufferFor, flush: flush, circleDab: circleDab, clear: clear, onTool: onTool,
        setOn: setOn, isOn: function () { return st.on; }, setColor: setColor, getColor: function () { return st.color; },
        syncUi: syncUi, state: st
    };
})(typeof window === 'object' ? window : globalThis);
