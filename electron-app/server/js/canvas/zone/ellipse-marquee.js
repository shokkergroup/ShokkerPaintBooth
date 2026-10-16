(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBEllipseMarquee = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // PORT-W1 (2026-10-09): composeMask rasterises with exact anti-aliased
    // polygon coverage from SPBPcSelection (PhotoCraft selection.rs polygon)
    // instead of a hard per-pixel inside test. window.SPB_PC_W1_OFF = true
    // restores the hard-edged legacy rasteriser.
    const G = typeof window !== 'undefined' ? window : globalThis;
    function pcCore() {
        if (G.SPB_PC_W1_OFF) return null;
        if (G.SPBPcSelection) return G.SPBPcSelection;
        try { if (typeof require === 'function') return require('../pc-selection-core.js'); } catch (e) { /* legacy path */ }
        return null;
    }

    function point(value) {
        return {
            x: Number(value && value.x) || 0,
            y: Number(value && value.y) || 0,
        };
    }

    // SPB-93 tick 21, owner verdict: tools still feel "jinky/off." Keep the
    // gesture geometry pure so preview and commit share Photoshop-style Shift
    // circle + Alt-from-center semantics. Served before -> after: six-point
    // drag 238 ms -> 173 ms; duplicate Add 2 Zone undos -> 1 real undo, then
    // Nothing to undo; the old 2048 guide was sub-pixel on screen.
    function resolveGesture(anchorValue, pointerValue, options) {
        const anchor = point(anchorValue);
        const pointer = point(pointerValue);
        const opts = options || {};
        let dx = pointer.x - anchor.x;
        let dy = pointer.y - anchor.y;
        if (opts.shiftKey && (dx || dy)) {
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            dx = size * Math.sign(dx || 1);
            dy = size * Math.sign(dy || 1);
        }
        const start = opts.altKey
            ? { x: anchor.x - dx, y: anchor.y - dy }
            : anchor;
        const end = { x: anchor.x + dx, y: anchor.y + dy };
        return {
            start,
            end,
            cx: (start.x + end.x) / 2,
            cy: (start.y + end.y) / 2,
            rx: Math.abs(end.x - start.x) / 2,
            ry: Math.abs(end.y - start.y) / 2,
        };
    }

    function validateGesture(gestureValue, minimumDiameterValue) {
        const gesture = gestureValue || {};
        const minimumDiameter = Math.max(2, Number(minimumDiameterValue) || 2);
        const width = (Number(gesture.rx) || 0) * 2;
        const height = (Number(gesture.ry) || 0) * 2;
        if (width < minimumDiameter || height < minimumDiameter) {
            return { valid: false, reason: 'Selection too small' };
        }
        return { valid: true, reason: '' };
    }

    function dirtyRect(gestureValue, width, height, paddingValue) {
        const gesture = gestureValue || {};
        if (width < 1 || height < 1) return null;
        const padding = Math.max(0, Number(paddingValue) || 0);
        const x1 = Math.max(0, Math.floor((Number(gesture.cx) || 0) - (Number(gesture.rx) || 0) - padding));
        const y1 = Math.max(0, Math.floor((Number(gesture.cy) || 0) - (Number(gesture.ry) || 0) - padding));
        const x2 = Math.min(width, Math.ceil((Number(gesture.cx) || 0) + (Number(gesture.rx) || 0) + padding + 1));
        const y2 = Math.min(height, Math.ceil((Number(gesture.cy) || 0) + (Number(gesture.ry) || 0) + padding + 1));
        return { x: x1, y: y1, width: Math.max(0, x2 - x1), height: Math.max(0, y2 - y1) };
    }

    function countDifferences(a, b) {
        if (!a || !b || a.length !== b.length) return Infinity;
        let changed = 0;
        for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) changed++;
        return changed;
    }

    function composeMask(currentMask, widthValue, heightValue, gestureValue, modeValue) {
        const width = Math.max(0, Math.floor(Number(widthValue) || 0));
        const height = Math.max(0, Math.floor(Number(heightValue) || 0));
        const length = width * height;
        const current = currentMask instanceof Uint8Array && currentMask.length === length
            ? currentMask
            : new Uint8Array(length);
        const mode = modeValue === 'subtract' || modeValue === 'replace' ? modeValue : 'add';
        const next = mode === 'replace' ? new Uint8Array(length) : new Uint8Array(current);
        const gesture = gestureValue || {};
        const cx = Number(gesture.cx) || 0;
        const cy = Number(gesture.cy) || 0;
        const rx = Math.abs(Number(gesture.rx) || 0);
        const ry = Math.abs(Number(gesture.ry) || 0);
        if (!length || rx < 1 || ry < 1) {
            return { nextMask: next, enclosedPixels: 0, changedPixels: countDifferences(current, next) };
        }
        const pc = pcCore();
        if (pc) {
            const cover = pc.ellipse(cx, cy, rx, ry, width, height, true);
            const composed = pc.compose(current, cover.mask, mode);
            let pcEnclosed = 0;
            if (cover.bbox) {
                for (let y = cover.bbox.y0; y < cover.bbox.y1; y++) {
                    for (let x = cover.bbox.x0; x < cover.bbox.x1; x++) if (cover.mask[y * width + x] > 127) pcEnclosed++;
                }
            }
            return { nextMask: composed, enclosedPixels: pcEnclosed, changedPixels: countDifferences(current, composed) };
        }
        const rx2 = rx * rx;
        const ry2 = ry * ry;
        const minX = Math.max(0, Math.floor(cx - rx));
        const maxX = Math.min(width - 1, Math.ceil(cx + rx));
        const minY = Math.max(0, Math.floor(cy - ry));
        const maxY = Math.min(height - 1, Math.ceil(cy + ry));
        let enclosedPixels = 0;
        for (let y = minY; y <= maxY; y++) {
            for (let x = minX; x <= maxX; x++) {
                const dx = x - cx;
                const dy = y - cy;
                if ((dx * dx) / rx2 + (dy * dy) / ry2 > 1) continue;
                enclosedPixels++;
                next[y * width + x] = mode === 'subtract' ? 0 : 255;
            }
        }
        return {
            nextMask: next,
            enclosedPixels,
            changedPixels: countDifferences(current, next),
        };
    }

    return { resolveGesture, validateGesture, dirtyRect, composeMask, countDifferences };
});
