/* SPBPcQuad - skew / distort / perspective handles for the whole-Layer Free Transform.
   Bakes through SPBPcWarp (PhotoCraft transform.rs homography warp, (c) 2026 ArtCraft Team and the PhotoCraft
   contributors, MIT OR Apache-2.0 - see THIRD_PARTY_NOTICES.md). SPB lane PORT-W3, 2026-10-09.

   Photoshop-style modifiers (start the drag with the key held):
     Ctrl + drag a CORNER ............ Distort (free 4-corner); +Shift locks to the dominant axis
     Ctrl + Shift + drag an EDGE ..... Skew (the edge slides along itself)
     Ctrl + Shift + Alt + CORNER ..... Perspective (the neighbouring corner mirrors, trapezoid stays symmetric)
   Once a quad exists the layer is in free-form mode: plain drags on corners = distort, edges = skew,
   inside = move, outside click / double-click / Apply = bake, Cancel / Esc = discard. Arrow keys nudge (Shift = 8 px).
   Whole-layer transforms only (no picked-element sub-rect). Kill switch: window.SPB_PC_W3_OFF = true.
   [SPB-TFX1 2026-10-09 TA-031] Ctrl+T now boxes the layer's content (TA-028), which is an isolated PIECE session, so distort / skew / perspective
   work on a piece too (composePiece: the piece crop is warped through the quad and put back into the layer, its old footprint cleared;
   window.SPB_TFX1_OFF = true = whole-layer sessions only, as before). */
(function (root) {
    'use strict';
    const api = {};
    let drag = null, installed = false;

    function state() { try { return (typeof freeTransformState !== 'undefined') ? freeTransformState : null; } catch (_e) { return null; } }
    function off() { return !!(root.SPB_PC_W3_OFF) || !root.SPBPcWarp; }
    // [SPB-TFX1 2026-10-09 TA-031] a piece session (subRect) is eligible too, unless SPB_TFX1_OFF
    function eligible(s) { return !!(s && s.target === 'layer' && s.origImg && ((!s.subRect && !s.origSubRect) || (!root.SPB_TFX1_OFF && (s.origSubRect || s.subRect) && s.origBbox))); }
    function pos(e) {
        if (typeof _transformGetPixel === 'function') { const p = _transformGetPixel(e, true); if (p) return p; }
        const pc = document.getElementById('paintCanvas'), r = pc.getBoundingClientRect();
        return { x: (e.clientX - r.left) * pc.width / r.width, y: (e.clientY - r.top) * pc.height / r.height };
    }
    function pps() { try { return (typeof _transformCanvasPxPerScreenPx === 'function') ? _transformCanvasPxPerScreenPx() : 1; } catch (_e) { return 1; } }

    // box params -> quad (tl,tr,br,bl); same order the canvas path uses: translate(C) scale(flip) rotate(rot)
    function cornersFromState(s) {
        const w = Math.max(1, Math.abs(s.boxW)), h = Math.max(1, Math.abs(s.boxH));
        const fx = (s.scaleX || 1) < 0 ? -1 : 1, fy = (s.scaleY || 1) < 0 ? -1 : 1, a = (s.rotation || 0) * Math.PI / 180, c = Math.cos(a), sn = Math.sin(a);
        return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(function (p) {
            return [s.centerX + fx * (p[0] * c - p[1] * sn), s.centerY + fy * (p[0] * sn + p[1] * c)];
        });
    }
    function cross(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
    function validQuad(q) { // convex + non-degenerate keeps the homography stable
        let sign = 0;
        for (let i = 0; i < 4; i++) {
            const c = cross(q[i], q[(i + 1) % 4], q[(i + 2) % 4]);
            if (Math.abs(c) < 1) return false;
            const sg = c > 0 ? 1 : -1;
            if (sign && sg !== sign) return false;
            sign = sg;
        }
        return true;
    }
    function hit(q, p) {
        const k = pps(), rc = Math.max(12, 11 * k), re = Math.max(10, 9 * k);
        for (let i = 0; i < 4; i++) if (Math.hypot(q[i][0] - p.x, q[i][1] - p.y) <= rc) return { kind: 'corner', i: i };
        for (let i = 0; i < 4; i++) {
            const a = q[i], b = q[(i + 1) % 4];
            if (Math.hypot((a[0] + b[0]) / 2 - p.x, (a[1] + b[1]) / 2 - p.y) <= re) return { kind: 'edge', i: i };
        }
        // inside (point in convex quad)
        let sign = 0, inside = true;
        for (let i = 0; i < 4; i++) { const c = cross(q[i], q[(i + 1) % 4], [p.x, p.y]); const sg = c >= 0 ? 1 : -1; if (sign && sg !== sign) { inside = false; break; } sign = sg; }
        return inside ? { kind: 'inside' } : null;
    }
    function redraw() {
        if (typeof drawTransformHandles === 'function') drawTransformHandles();
        if (typeof renderContextActionBar === 'function') renderContextActionBar();
    }

    function onDown(e) {
        if (off() || e.button !== 0) return;
        const s = state();
        if (!eligible(s)) return;
        const entering = !s.quad;
        if (entering && !(e.ctrlKey || e.metaKey)) return; // normal handles keep working until Ctrl is used
        const p = pos(e), q = s.quad || cornersFromState(s);
        const h = hit(q, p);
        if (entering && (!h || h.kind === 'inside')) return;
        e.preventDefault(); e.stopImmediatePropagation();
        if (!h) { if (typeof commitLayerTransform === 'function') commitLayerTransform(); return; }
        if (e.detail === 2 && !entering) { if (typeof commitLayerTransform === 'function') commitLayerTransform(); return; }
        if (entering) {
            s.quad = q.map(function (v) { return v.slice(); });
            if (typeof showToast === 'function') showToast('Distort: drag corners • Ctrl+Shift+Alt = perspective • edges = skew • Apply to bake', 'info');
        }
        let mode = 'move';
        if (h.kind === 'corner') mode = (e.shiftKey && e.altKey) ? 'perspective' : 'distort';
        else if (h.kind === 'edge') mode = 'skew';
        drag = { mode: mode, h: h, p0: p, q0: s.quad.map(function (v) { return v.slice(); }), shift: e.shiftKey };
        document.addEventListener('mousemove', onMove, true);
        document.addEventListener('mouseup', onUp, true);
        redraw();
    }
    function onMove(e) {
        const s = state();
        if (!drag || !eligible(s) || !s.quad) return;
        e.preventDefault(); e.stopImmediatePropagation();
        const p = pos(e);
        let dx = p.x - drag.p0.x, dy = p.y - drag.p0.y;
        const q0 = drag.q0, q = q0.map(function (v) { return v.slice(); }), i = drag.h.i;
        if (drag.mode === 'move') { for (let k = 0; k < 4; k++) { q[k][0] += dx; q[k][1] += dy; } }
        else if (drag.mode === 'distort') {
            if (e.shiftKey) { if (Math.abs(dx) >= Math.abs(dy)) dy = 0; else dx = 0; }
            q[i][0] += dx; q[i][1] += dy;
        } else if (drag.mode === 'perspective') {
            if (Math.abs(dx) >= Math.abs(dy)) { // horizontal partner (tl<->tr, bl<->br)
                const j = [1, 0, 3, 2][i]; q[i][0] += dx; q[j][0] -= dx;
            } else { const j = [3, 2, 1, 0][i]; q[i][1] += dy; q[j][1] -= dy; }
        } else if (drag.mode === 'skew') {
            const a = q0[i], b = q0[(i + 1) % 4], vx = b[0] - a[0], vy = b[1] - a[1], len = Math.hypot(vx, vy) || 1;
            const t = (dx * vx + dy * vy) / len, ux = vx / len, uy = vy / len;
            q[i][0] += ux * t; q[i][1] += uy * t; q[(i + 1) % 4][0] += ux * t; q[(i + 1) % 4][1] += uy * t;
        }
        if (validQuad(q)) { s.quad = q; redraw(); }
    }
    function onUp(e) {
        document.removeEventListener('mousemove', onMove, true);
        document.removeEventListener('mouseup', onUp, true);
        if (drag) { e.stopImmediatePropagation(); drag = null; redraw(); }
    }
    function onKey(e) {
        const s = state();
        if (off() || !eligible(s) || !s.quad) return;
        const k = e.key;
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(k)) return;
        const t = e.target; if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
        const step = e.shiftKey ? 8 : 1, dx = k === 'ArrowLeft' ? -step : k === 'ArrowRight' ? step : 0, dy = k === 'ArrowUp' ? -step : k === 'ArrowDown' ? step : 0;
        s.quad = s.quad.map(function (v) { return [v[0] + dx, v[1] + dy]; });
        e.preventDefault(); e.stopImmediatePropagation(); redraw();
    }

    // Overlay: outline + the same white/cyan square handles as the box transform. Returns true when it drew.
    api.drawHandles = function (ctx, s) {
        if (off() || !eligible(s) || !s.quad) return false;
        const q = s.quad, hs = (typeof _getLayerSubRectHandleRadius === 'function') ? _getLayerSubRectHandleRadius(s) : 6.5, ehs = Math.max(4, 4.5 * pps());
        ctx.save();
        ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 2; ctx.beginPath();
        ctx.moveTo(q[0][0], q[0][1]); for (let i = 1; i < 4; i++) ctx.lineTo(q[i][0], q[i][1]); ctx.closePath(); ctx.stroke();
        for (let i = 0; i < 4; i++) {
            const a = q[i], b = q[(i + 1) % 4], mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
            ctx.fillStyle = '#fff'; ctx.strokeStyle = '#00aacc'; ctx.lineWidth = 1;
            ctx.fillRect(mx - ehs, my - ehs, ehs * 2, ehs * 2); ctx.strokeRect(mx - ehs, my - ehs, ehs * 2, ehs * 2);
        }
        for (let i = 0; i < 4; i++) {
            ctx.fillStyle = '#fff'; ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 1.5;
            ctx.fillRect(q[i][0] - hs, q[i][1] - hs, hs * 2, hs * 2); ctx.strokeRect(q[i][0] - hs, q[i][1] - hs, hs * 2, hs * 2);
        }
        ctx.restore();
        return true;
    };
    // Apply: bake origImg through the quad into layer.img / bbox (the caller already pushed ONE undo step).
    api.bake = function (s, layer) {
        if (off() || !s || !s.quad || !layer) return false;
        if (s.subRect || s.origSubRect) return false;   // [SPB-TFX1 2026-10-09 TA-031] pieces go through composePiece (the caller records the undo step first)
        const baked = root.SPBPcWarp.bakeQuad(s.origImg, s.quad);
        if (!baked) { if (typeof showToast === 'function') showToast('Distort could not be rasterized - layer unchanged', 'warn'); return false; }
        layer.img = baked.canvas; layer.bbox = baked.bbox;
        return true;
    };
    // [SPB-TFX1 2026-10-09 TA-031] piece session: warp the crop of the piece through the quad, clear the piece's old footprint, put the warp back.
    // Returns { canvas, bbox } (a union surface, like composeElementTransforms) or null. createCanvas(w,h) supplies the destination.
    api.composePiece = function (s, createCanvas, opts) {
        if (off() || !s || !s.quad || !s.origImg || typeof createCanvas !== 'function') return null;
        const rect = s.origSubRect || s.subRect, bb = s.origBbox;
        if (!rect || !bb || bb.length < 4) return null;
        const src = s.origImg, sw0 = src.naturalWidth || src.width, sh0 = src.naturalHeight || src.height;
        const bw = Math.max(1, bb[2] - bb[0]), bh = Math.max(1, bb[3] - bb[1]), kx = sw0 / bw, ky = sh0 / bh;
        const rx1 = Math.max(bb[0], Math.min(bb[2], Number(rect.x1))), ry1 = Math.max(bb[1], Math.min(bb[3], Number(rect.y1)));
        const rx2 = Math.max(rx1, Math.min(bb[2], Number(rect.x2))), ry2 = Math.max(ry1, Math.min(bb[3], Number(rect.y2)));
        if (!(rx2 > rx1) || !(ry2 > ry1)) return null;
        const px = (rx1 - bb[0]) * kx, py = (ry1 - bb[1]) * ky, pw = (rx2 - rx1) * kx, ph = (ry2 - ry1) * ky;
        const pc = document.createElement('canvas'); pc.width = Math.max(1, Math.round(pw)); pc.height = Math.max(1, Math.round(ph));
        pc.getContext('2d').drawImage(src, px, py, pw, ph, 0, 0, pc.width, pc.height);
        const baked = root.SPBPcWarp.bakeQuad(pc, s.quad, opts);
        if (!baked) return null;
        const ux1 = Math.min(Math.floor(bb[0]), baked.bbox[0]), uy1 = Math.min(Math.floor(bb[1]), baked.bbox[1]);
        const ux2 = Math.max(Math.ceil(bb[2]), baked.bbox[2]), uy2 = Math.max(Math.ceil(bb[3]), baked.bbox[3]);
        const w = ux2 - ux1, h = uy2 - uy1;
        if (!(w > 0) || !(h > 0) || w * h > 64e6) return null;
        const dest = createCanvas(w, h), ctx = dest.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(src, 0, 0, sw0, sh0, bb[0] - ux1, bb[1] - uy1, bw, bh);
        ctx.clearRect(rx1 - ux1, ry1 - uy1, rx2 - rx1, ry2 - ry1);
        ctx.drawImage(baked.canvas, baked.bbox[0] - ux1, baked.bbox[1] - uy1);
        return { canvas: dest, bbox: [ux1, uy1, ux2, uy2] };
    };
    api.cornersFromState = cornersFromState; api.validQuad = validQuad;
    api.install = function () {
        if (installed) return; const tc = document.getElementById('transformCanvas'); if (!tc) return;
        installed = true;
        tc.addEventListener('mousedown', onDown, true);
        root.addEventListener('keydown', onKey, true);
    };
    root.SPBPcQuad = api;
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', api.install); else api.install();
        // transformCanvas may be created late
        setTimeout(api.install, 1500); setTimeout(api.install, 5000);
    }
})(typeof window !== 'undefined' ? window : globalThis);
