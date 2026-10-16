/* [SPB-TFX3 2026-10-09 PORT-1 Smart Guides + snapping, lane TOOLS-FIX-3] Port of PhotoCraft crates/engine/src/snap.rs
 * (SnapTargets: nearest / snap_rect / lines) to the SPB Move tool, plus Photoshop's arrow-key nudge.
 *
 * BEFORE (measured, fix3/sg_before.json, owner PSD, real mouse): dragging a number or sponsor near another one, or near the
 * middle of the car, snapped to NOTHING except two crude rules (the element CENTRE to the canvas edge / to where the drag started),
 * drew no guide, and the arrow keys did nothing in the Move tool (0 px nudge for 4 presses). Aligning two numbers or centring a
 * sponsor on the hood was an eyeball job; each pixel of error shows on the car.
 *
 * AFTER: while you drag a layer, a layer element or a zone piece, its left / centre / right and top / middle / bottom lines snap to
 * the canvas edges and centre lines, the selection box, and the visible edges and centres of the other (small) layers, within
 * 8 SCREEN px (so the pull is the same at every zoom). Magenta guides show what you snapped to (cyan for the canvas centre/edges).
 * Hold Ctrl to move freely, Shift keeps its straight-line meaning (no snapping while Shift is down). Arrow keys nudge the selected
 * layer / isolated element 1 px, Shift+Arrow 10 px, as ONE undo step per burst.
 *
 * Kill switch: window.SPB_TFX3_OFF = true (or localStorage SPB_TFX3_OFF='1') -> the old behaviour, byte for byte (hooks are no-ops).
 */
(function (root, factory) {
    var api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;       // node tests import the pure geometry
    if (root && root.document) root.SPBTfx3Guides = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';
    var isBrowser = !!(root && root.document);
    if (isBrowser) { try { if (root.SPB_TFX3_OFF !== true && root.localStorage.getItem('SPB_TFX3_OFF') === '1') root.SPB_TFX3_OFF = true; } catch (_e) { } }
    function off() { return !!(root && root.SPB_TFX3_OFF === true); }

    // ================================================================== pure geometry (port of snap.rs)
    // kinds: 'canvasEdge' 'canvasCenter' 'layerEdge' 'layerCenter' 'selection' 'guide'
    function Targets(extent) { this.x = []; this.y = []; this.extent = extent || [0, 0, 0, 0]; }
    Targets.prototype.addRect = function (r, edge, center) {
        var xs = [r[1], r[3]], ys = [r[0], r[2]];
        this.x.push({ pos: r[0], kind: edge, span: xs }, { pos: r[2], kind: edge, span: xs }, { pos: (r[0] + r[2]) / 2, kind: center, span: xs });
        this.y.push({ pos: r[1], kind: edge, span: ys }, { pos: r[3], kind: edge, span: ys }, { pos: (r[1] + r[3]) / 2, kind: center, span: ys });
    };
    Targets.prototype.isEmpty = function () { return !this.x.length && !this.y.length; };
    // closest target to v within tol on one axis (guides win ties, as in Photoshop / PhotoCraft)
    Targets.prototype.nearest = function (vertical, v, tol) {
        var list = vertical ? this.x : this.y, best = null, bd = 0;
        for (var i = 0; i < list.length; i++) {
            var t = list[i], d = Math.abs(t.pos - v);
            if (d > tol) continue;
            if (best === null || d < bd - 1e-9 || (Math.abs(d - bd) <= 1e-9 && t.kind === 'guide' && best.kind !== 'guide')) { best = t; bd = d; }
        }
        return best;
    };
    function line(vertical, t, a, b) { return { vertical: vertical, pos: t.pos, from: Math.min(t.span[0], a, b), to: Math.max(t.span[1], a, b), kind: t.kind }; }
    // snap a moving rectangle [x0,y0,x1,y1]: per axis the edge/centre closest to a target decides the correction
    Targets.prototype.snapRect = function (r, tol) {
        var delta = [0, 0], lines = [];
        for (var axis = 0; axis < 2; axis++) {
            var vertical = axis === 0, a = r[axis], b = r[axis + 2], anchors = [a, (a + b) / 2, b], best = null;
            for (var k = 0; k < 3; k++) {
                var t = this.nearest(vertical, anchors[k], tol);
                if (t) { var d = t.pos - anchors[k]; if (best === null || Math.abs(d) < Math.abs(best)) best = d; }
            }
            if (best === null) continue;
            delta[axis] = best;
            var other = vertical ? [r[1], r[3]] : [r[0], r[2]], list = vertical ? this.x : this.y;
            for (var m = 0; m < 3; m++) {
                var moved = anchors[m] + best, hit = null;
                for (var q = 0; q < list.length; q++) {
                    if (Math.abs(list[q].pos - moved) < 1e-6 && (hit === null || (list[q].kind === 'guide' && hit.kind !== 'guide'))) hit = list[q];
                }
                if (hit) lines.push(line(vertical, hit, other[0], other[1]));
            }
        }
        return { delta: delta, lines: lines };
    };
    function unionRects(rs) {
        var u = null;
        for (var i = 0; i < rs.length; i++) { var r = rs[i]; u = u ? [Math.min(u[0], r[0]), Math.min(u[1], r[1]), Math.max(u[2], r[2]), Math.max(u[3], r[3])] : r.slice(); }
        return u;
    }

    var api = { Targets: Targets, unionRects: unionRects, off: off, version: 'tfx3-sg-1' };
    if (!isBrowser) return api;

    // ================================================================== SPB document targets
    var PX_PER_SCREEN = 8;                   // snap pull in SCREEN px (PhotoCraft: 8 px / zoom)
    function stack() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : (root._psdLayers || []); }
    function cv() { return document.getElementById('paintCanvas'); }
    function pxPerScreen() {
        try { var c = cv(), r = c.getBoundingClientRect(); if (r.width > 0) return c.width / r.width; } catch (_e) { }
        return 1;
    }

    // tight box of a layer's non-transparent pixels in canvas coordinates (alpha > 8); null when empty / unreadable.
    // Big images are first scanned at <= 512 px (one drawImage + 262k px), then ONLY the found region is read at full resolution, so a
    // 2048 px blank layer costs ~3 ms instead of a 16 MB read-back. maxArea: give up (null) once the content is bigger than that.
    var tbCache = {};
    function tightBox(layer, maxArea) {
        try {
            var img = layer && layer.img, bb = layer && layer.bbox;
            if (!img || !bb) return null;
            var iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
            var bw = bb[2] - bb[0], bh = bb[3] - bb[1];
            if (!(iw > 0 && ih > 0 && bw > 0 && bh > 0)) return null;
            var ck = layer.id + '|' + iw + 'x' + ih + '|' + bb.join(',') + '|' + (root._spbLayerRev || 0) + '|' + (maxArea || 0);
            if (Object.prototype.hasOwnProperty.call(tbCache, ck)) return tbCache[ck];
            var res = null, rx0 = 0, ry0 = 0, rx1 = iw, ry1 = ih;
            if (iw * ih > 400000) {
                var s = Math.max(1, Math.ceil(Math.max(iw, ih) / 512)), dw = Math.ceil(iw / s), dh = Math.ceil(ih / s);
                var dc = document.createElement('canvas'); dc.width = dw; dc.height = dh;
                var dg = dc.getContext('2d', { willReadFrequently: true }); dg.imageSmoothingEnabled = true; dg.drawImage(img, 0, 0, dw, dh);
                var dd = dg.getImageData(0, 0, dw, dh).data, cx0 = dw, cy0 = dh, cx1 = -1, cy1 = -1;
                for (var y = 0; y < dh; y++) for (var x = 0; x < dw; x++) if (dd[(y * dw + x) * 4 + 3] > 0) { if (x < cx0) cx0 = x; if (x > cx1) cx1 = x; if (y < cy0) cy0 = y; if (y > cy1) cy1 = y; }
                if (cx1 < 0) { tbCache[ck] = null; return null; }
                rx0 = Math.max(0, (cx0 - 1) * s); ry0 = Math.max(0, (cy0 - 1) * s); rx1 = Math.min(iw, (cx1 + 2) * s); ry1 = Math.min(ih, (cy1 + 2) * s);
                if (maxArea && (rx1 - rx0) * (ry1 - ry0) * (bw / iw) * (bh / ih) > maxArea) { tbCache[ck] = null; return null; }
            }
            var rw = rx1 - rx0, rh = ry1 - ry0;
            var c = document.createElement('canvas'); c.width = rw; c.height = rh;
            var g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, -rx0, -ry0);
            var d = g.getImageData(0, 0, rw, rh).data, minX = rw, minY = rh, maxX = -1, maxY = -1;
            for (var yy = 0; yy < rh; yy++) {
                var row = yy * rw * 4;
                for (var xx = 0; xx < rw; xx++) {
                    if (d[row + xx * 4 + 3] > 8) { if (xx < minX) minX = xx; if (xx > maxX) maxX = xx; if (yy < minY) minY = yy; if (yy > maxY) maxY = yy; }
                }
            }
            if (maxX >= 0) {
                var sx = bw / iw, sy = bh / ih;
                res = [bb[0] + (rx0 + minX) * sx, bb[1] + (ry0 + minY) * sy, bb[0] + (rx0 + maxX + 1) * sx, bb[1] + (ry0 + maxY + 1) * sy];
            }
            var keys = Object.keys(tbCache); if (keys.length > 80) delete tbCache[keys[0]];
            tbCache[ck] = res; return res;
        } catch (_e) { return null; }
    }

    var gesture = null;                      // { key, targets, moving } cached for one drag
    function selectionBounds() {
        try {
            var zs = (typeof zones !== 'undefined') ? zones : null, i = (typeof selectedZoneIndex === 'number') ? selectedZoneIndex : -1;
            var m = zs && i >= 0 && zs[i] && zs[i].regionMask;
            if (!m || !m.length) return null;
            var W = Math.round(Math.sqrt(m.length)), x0 = W, y0 = W, x1 = -1, y1 = -1;
            for (var k = 0; k < m.length; k++) {
                if (m[k] >= 128) { var x = k % W, y = (k / W) | 0; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
            }
            return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
        } catch (_e) { return null; }
    }
    function buildTargets(excludeId) {
        var c = cv(); if (!c) return null;
        var W = c.width, H = c.height, t = new Targets([0, 0, W, H]);
        t.addRect([0, 0, W, H], 'canvasEdge', 'canvasCenter');
        var L = stack(), area = W * H;
        for (var i = 0; i < L.length; i++) {
            var l = L[i];
            if (!l || l.id === excludeId || !l.visible || !l.bbox) continue;
            var r = tightBox(l, area * 0.45);            // base / template layers (content > 45% of the car) are skipped: their edges are the canvas, not an object
            if (r && (r[2] - r[0]) * (r[3] - r[1]) <= area * 0.45) t.addRect(r, 'layerEdge', 'layerCenter');
        }
        var sb = selectionBounds();
        if (sb) {
            t.x.push({ pos: sb[0], kind: 'selection', span: [sb[1], sb[3]] }, { pos: sb[2], kind: 'selection', span: [sb[1], sb[3]] });
            t.y.push({ pos: sb[1], kind: 'selection', span: [sb[0], sb[2]] }, { pos: sb[3], kind: 'selection', span: [sb[0], sb[2]] });
        }
        return t;
    }
    function targetsFor(key, excludeId) {
        if (!gesture || gesture.key !== key) gesture = { key: key, targets: buildTargets(excludeId), movingBox: null };
        return gesture.targets;
    }

    // ================================================================== overlay
    var ctrlDown = false, shiftDown = false, lastLines = null;
    function overlay() {
        var g = document.getElementById('spbTfx3Guides'), pc = cv();
        if (!pc) return null;
        if (!g) {
            var tc = document.getElementById('transformCanvas'), host = (tc && tc.parentNode) || pc.parentNode;
            if (!host) return null;
            g = document.createElement('canvas'); g.id = 'spbTfx3Guides'; g.setAttribute('aria-hidden', 'true');
            g.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:16;display:none;';
            host.appendChild(g);
        }
        if (g.width !== pc.width) g.width = pc.width;
        if (g.height !== pc.height) g.height = pc.height;
        g.style.width = pc.style.width; g.style.height = pc.style.height;
        return g;
    }
    function draw(lines, box) {
        lastLines = lines;
        var g = overlay(); if (!g) return;
        var ctx = g.getContext('2d');
        ctx.clearRect(0, 0, g.width, g.height);
        if (!lines || !lines.length) { g.style.display = 'none'; return; }
        g.style.display = 'block';
        var k = pxPerScreen(), lw = Math.max(1, 1.25 * k);
        ctx.lineWidth = lw; ctx.lineCap = 'butt';
        for (var i = 0; i < lines.length; i++) {
            var l = lines[i], canvasKind = (l.kind === 'canvasCenter' || l.kind === 'canvasEdge');
            ctx.strokeStyle = canvasKind ? '#2bd9ff' : (l.kind === 'selection' ? '#ffd23a' : '#ff2bd6');
            ctx.setLineDash(l.kind === 'canvasEdge' ? [6 * k, 4 * k] : []);
            ctx.beginPath();
            if (l.vertical) { ctx.moveTo(l.pos + 0.5 * 0, l.from); ctx.lineTo(l.pos, l.to); } else { ctx.moveTo(l.from, l.pos); ctx.lineTo(l.to, l.pos); }
            ctx.stroke();
            // little end ticks like Photoshop's smart guides
            ctx.setLineDash([]);
            var tk = 4 * k;
            ctx.beginPath();
            if (l.vertical) { ctx.moveTo(l.pos - tk, l.from); ctx.lineTo(l.pos + tk, l.from); ctx.moveTo(l.pos - tk, l.to); ctx.lineTo(l.pos + tk, l.to); }
            else { ctx.moveTo(l.from, l.pos - tk); ctx.lineTo(l.from, l.pos + tk); ctx.moveTo(l.to, l.pos - tk); ctx.lineTo(l.to, l.pos + tk); }
            ctx.stroke();
        }
    }
    function clear() {
        gesture = null; lastLines = null;
        var g = document.getElementById('spbTfx3Guides');
        if (g) { try { g.getContext('2d').clearRect(0, 0, g.width, g.height); } catch (_e) { } g.style.display = 'none'; }
    }

    // ================================================================== hooks used by paint-booth-3-canvas.js
    function snapWith(key, excludeId, box, e) {
        if (off() || ctrlDown || (e && (e.ctrlKey || e.metaKey)) || (e && e.shiftKey) || shiftDown) { draw(null); return null; }
        var t = targetsFor(key, excludeId);
        if (!t || t.isEmpty()) return null;
        var res = t.snapRect(box, PX_PER_SCREEN * pxPerScreen());
        var moved = [box[0] + res.delta[0], box[1] + res.delta[1], box[2] + res.delta[0], box[3] + res.delta[1]];
        // a guide spans from the snapped object to the target object (snap.rs line())
        draw(res.lines, moved);
        return res;
    }

    // free-transform move of a layer element / zone piece. (moveX, moveY) = proposed CENTRE; returns the snapped centre or null.
    function snapElementMove(s, moveX, moveY, e) {
        if (!s) return null;
        var sr = s.subRect, w, h;
        if (sr) { w = sr.x2 - sr.x1; h = sr.y2 - sr.y1; } else { w = s.boxW; h = s.boxH; }
        if (!(w > 0 && h > 0)) return null;
        var key = 'ft:' + (s.target || '') + ':' + (s.layerId || '') + ':' + (s.dragStartCX | 0) + ',' + (s.dragStartCY | 0) + ':' + (s.dragStartX | 0) + ',' + (s.dragStartY | 0);
        // rotated pieces: only the centre lines make sense (the AABB is not the object)
        var rot = Math.abs(s.rotation || 0) % 180, rotated = rot > 0.5 && Math.abs(rot - 180) > 0.5;
        var cx = sr ? (sr.x1 + sr.x2) / 2 : moveX, cy = sr ? (sr.y1 + sr.y2) / 2 : moveY;      // the sub-rect is already at the proposed position
        var box = rotated ? [cx, cy, cx, cy] : [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
        var res = snapWith(key, s.layerId || null, box, e);
        if (!res) return null;
        var dx = res.delta[0], dy = res.delta[1];
        if (sr) { sr.x1 += dx; sr.x2 += dx; sr.y1 += dy; sr.y2 += dy; }
        return { x: moveX + dx, y: moveY + dy, dx: dx, dy: dy };
    }

    var dragCache = null;                    // content box of the dragged layer, per drag
    // whole-layer drag: (dx, dy) = proposed shift from drag start; returns snapped shift or null
    function snapLayerDrag(layer, state, dx, dy) {
        if (!layer || !state) return null;
        if (!dragCache || dragCache.state !== state) dragCache = { state: state, box: tightBox({ id: layer.id, img: layer.img, bbox: state.origBbox }) || state.origBbox.slice() };
        var b = dragCache.box, box = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy];
        var res = snapWith('ld:' + state.layerId + ':' + state.startX + ',' + state.startY, state.layerId, box, null);
        if (!res) return null;
        return { dx: dx + res.delta[0], dy: dy + res.delta[1] };
    }

    // ================================================================== key state + guide cleanup
    document.addEventListener('keydown', function (e) { if (e.key === 'Control') ctrlDown = true; if (e.key === 'Shift') shiftDown = true; }, true);
    document.addEventListener('keyup', function (e) { if (e.key === 'Control') ctrlDown = false; if (e.key === 'Shift') shiftDown = false; }, true);
    window.addEventListener('blur', function () { ctrlDown = false; shiftDown = false; });
    document.addEventListener('mouseup', function () { if (lastLines || gesture) setTimeout(clear, 0); dragCache = null; }, true);

    // ================================================================== arrow-key nudge (Move tool)
    var nudgeAt = 0, nudgeTimer = 0;
    function typing() { var a = document.activeElement, t = a && a.tagName; return t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT' || (a && a.isContentEditable); }
    function nudgeKey(e) {
        if (off() || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
        var dx = 0, dy = 0, step = e.shiftKey ? 10 : 1;
        if (e.key === 'ArrowLeft') dx = -step; else if (e.key === 'ArrowRight') dx = step; else if (e.key === 'ArrowUp') dy = -step; else if (e.key === 'ArrowDown') dy = step; else return;
        if (typing() || typeof canvasMode === 'undefined' || canvasMode !== 'layer-move') return;
        if (typeof isLayerToolbarMode === 'function' && !isLayerToolbarMode()) return;
        var s = (typeof freeTransformState !== 'undefined') ? freeTransformState : null;
        if (s && s.target === 'layer') {                      // isolated element / transform in progress: move the box, commit stays Enter
            s.centerX += dx; s.centerY += dy;
            if (s.subRect) { s.subRect.x1 += dx; s.subRect.x2 += dx; s.subRect.y1 += dy; s.subRect.y2 += dy; }
            try { if (window.SPBElementTransformState && window.SPBElementTransformState.syncFrame) window.SPBElementTransformState.syncFrame(s); } catch (_e) { }
            if (typeof drawTransformHandles === 'function') drawTransformHandles();
            e.preventDefault(); e.stopPropagation(); return;
        }
        if (s) return;                                        // a zone transform owns the arrows
        var layer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
        if (!layer || !Array.isArray(layer.bbox) || !layer.visible) return;
        if (layer.locked) { if (typeof showToast === 'function') showToast('"' + (layer.name || 'Layer') + '" is locked — unlock it before moving', 'warn'); e.preventDefault(); return; }
        var now = Date.now();
        if (now - nudgeAt > 900 && typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('nudge layer');   // one undo step per burst
        nudgeAt = now;
        layer.bbox = [layer.bbox[0] + dx, layer.bbox[1] + dy, layer.bbox[2] + dx, layer.bbox[3] + dy];
        try { if (typeof recompositeFromLayers === 'function') recompositeFromLayers({ readback: false }); } catch (_e) { }
        try { if (typeof drawLayerBounds === 'function') drawLayerBounds(); } catch (_e) { }
        clearTimeout(nudgeTimer);
        nudgeTimer = setTimeout(function () {                // publish the final state once the burst ends (same as endLayerDrag)
            try { if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); } catch (_e) { }
            try { if (typeof drawLayerBounds === 'function') drawLayerBounds(); } catch (_e) { }
            try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); } catch (_e) { }
        }, 350);
        e.preventDefault(); e.stopPropagation();
    }
    document.addEventListener('keydown', nudgeKey, false);

    // [SPB-TFX3 2026-10-09 AUDIT2-F5 lane TOOLS-FIX-3, NEWUSER-QA #5] double-click a LIVE text layer with the Move tool = edit its text (Photoshop does the
    // same); before this a double-click with Move did nothing on text (and, after the old element isolation, "applied" a torn piece).
    document.addEventListener('dblclick', function (e) {
        try {
            if (off() || typeof canvasMode === 'undefined' || canvasMode !== 'layer-move') return;
            if (typeof isLayerToolbarMode === 'function' && !isLayerToolbarMode()) return;
            if (typeof freeTransformState !== 'undefined' && freeTransformState) return;
            var c = document.getElementById('paintCanvas'); if (!c || !e.target || !(e.target === c || e.target.id === 'transformCanvas' || (e.target.closest && e.target.closest('#paintCanvas')))) return;
            var layer = (typeof getSelectedLayer === 'function') ? getSelectedLayer() : null;
            if (!layer || layer.locked || !layer.visible || !layer.img || !layer.img.__spbText || !Array.isArray(layer.bbox)) return;
            var r = c.getBoundingClientRect(); if (!r.width || !r.height) return;
            var x = (e.clientX - r.left) * c.width / r.width, y = (e.clientY - r.top) * c.height / r.height;
            if (x < layer.bbox[0] || y < layer.bbox[1] || x > layer.bbox[2] || y > layer.bbox[3]) return;
            if (!window.SPBTextEdit || typeof window.SPBTextEdit.handleClick !== 'function' || typeof setCanvasMode !== 'function') return;
            e.preventDefault(); e.stopPropagation();
            setCanvasMode('text');
            window.SPBTextEdit.handleClick(x, y);
        } catch (_e) { }
    }, true);

    api.snapElementMove = snapElementMove; api.snapLayerDrag = snapLayerDrag; api.clear = clear; api.tightBox = tightBox;
    api.buildTargets = buildTargets; api.draw = draw;
    api.state = function () { return { lines: lastLines ? lastLines.length : 0, ctrl: ctrlDown, off: off() }; };
    return api;
});
