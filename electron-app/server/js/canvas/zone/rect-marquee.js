(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBRectMarquee = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function point(value) {
        return {
            x: Number(value && value.x) || 0,
            y: Number(value && value.y) || 0,
        };
    }

    // SPB-93 tick 22, owner verdict: tools still feel "jinky/off." Preview and
    // commit share this pure Photoshop-style Shift-square / Alt-center geometry.
    // Served before -> after: six-point drag 253 ms -> 123 ms; click-only and
    // identical empty rectangles 1 fake Zone undo each -> 0.
    function resolveGesture(anchorValue, pointerValue, options) {
        const anchor = point(anchorValue);
        const pointer = point(pointerValue);
        const opts = options || {};
        let dx = pointer.x - anchor.x;
        let dy = pointer.y - anchor.y;
        if (opts.fixedSize && opts.fixedSize.w > 0 && opts.fixedSize.h > 0) {
            dx = Number(opts.fixedSize.w) * Math.sign(dx || 1);
            dy = Number(opts.fixedSize.h) * Math.sign(dy || 1);
        } else if (opts.fixedAspect && opts.fixedAspect.w > 0 && opts.fixedAspect.h > 0 && dx) {
            dy = Math.abs(dx) * Number(opts.fixedAspect.h) / Number(opts.fixedAspect.w) * Math.sign(dy || 1);
        } else if (opts.shiftKey && (dx || dy)) {
            const size = Math.max(Math.abs(dx), Math.abs(dy));
            dx = size * Math.sign(dx || 1);
            dy = size * Math.sign(dy || 1);
        }
        const start = opts.altKey
            ? { x: anchor.x - dx, y: anchor.y - dy }
            : anchor;
        const end = { x: anchor.x + dx, y: anchor.y + dy };
        const x1 = Math.min(start.x, end.x);
        const y1 = Math.min(start.y, end.y);
        const x2 = Math.max(start.x, end.x);
        const y2 = Math.max(start.y, end.y);
        return { start, end, x1, y1, x2, y2, width: x2 - x1, height: y2 - y1 };
    }

    function validateGesture(gestureValue, minimumSizeValue) {
        const gesture = gestureValue || {};
        const minimumSize = Math.max(2, Number(minimumSizeValue) || 2);
        if ((Number(gesture.width) || 0) < minimumSize || (Number(gesture.height) || 0) < minimumSize) {
            return { valid: false, reason: 'Rectangle selection is too small' };
        }
        return { valid: true, reason: '' };
    }

    function dirtyRect(gestureValue, width, height, paddingValue) {
        const gesture = gestureValue || {};
        if (width < 1 || height < 1) return null;
        const padding = Math.max(0, Number(paddingValue) || 0);
        const x1 = Math.max(0, Math.floor((Number(gesture.x1) || 0) - padding));
        const y1 = Math.max(0, Math.floor((Number(gesture.y1) || 0) - padding));
        const x2 = Math.min(width, Math.ceil((Number(gesture.x2) || 0) + padding + 1));
        const y2 = Math.min(height, Math.ceil((Number(gesture.y2) || 0) + padding + 1));
        return { x: x1, y: y1, width: Math.max(0, x2 - x1), height: Math.max(0, y2 - y1) };
    }

    function countDifferences(a, b) {
        if (!a || !b || a.length !== b.length) return Infinity;
        let changed = 0, i = 0;
        // SPB-93 tools 2026-09-07, owner: eliminate laggy selection drags.
        // Replace composition took29ms at4096; identical native bytes need no
        // individual comparisons. XOR still counts each changed soft pixel.
        const bytes = value => value instanceof Uint8Array || value instanceof Uint8ClampedArray;
        if (bytes(a) && bytes(b) && (a.byteOffset & 3) === 0 && (b.byteOffset & 3) === 0) {
            const length = a.length >>> 2;
            const aw = new Uint32Array(a.buffer, a.byteOffset, length);
            const bw = new Uint32Array(b.buffer, b.byteOffset, length);
            for (let w = 0; w < length; w++) {
                const diff = aw[w] ^ bw[w];
                if (!diff) continue;
                if (diff & 0xff) changed++;
                if (diff & 0xff00) changed++;
                if (diff & 0xff0000) changed++;
                if (diff & 0xff000000) changed++;
            }
            i = length << 2;
        }
        for (; i < a.length; i++) if (a[i] !== b[i]) changed++;
        return changed;
    }

    function _tfx2Off() {
        try { return !!((typeof window !== 'undefined' && window.SPB_TFX2_OFF) || (typeof globalThis !== 'undefined' && globalThis.SPB_TFX2_OFF)); } catch (e) { return false; }
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
        const minX = Math.max(0, Math.min(width - 1, Math.floor(Number(gesture.x1) || 0)));
        // [SPB-TFX2 2026-10-09 TA-018] the gesture end is the pointer's pixel INDEX, so the rectangle is [x1, x2) like Photoshop: the old inclusive
        // ceil(x2) made every selection 1-2 px too large (drag 400x300 -> bbox 402x301 = 121,002 px).
        const endAdj = _tfx2Off() ? 0 : 1;
        const maxX = Math.max(0, Math.min(width - 1, Math.ceil(Number(gesture.x2) || 0) - endAdj));
        const minY = Math.max(0, Math.min(height - 1, Math.floor(Number(gesture.y1) || 0)));
        const maxY = Math.max(0, Math.min(height - 1, Math.ceil(Number(gesture.y2) || 0) - endAdj));
        let enclosedPixels = 0;
        let changedPixels = 0;
        const value = mode === 'subtract' ? 0 : 255;
        if (length && maxX >= minX && maxY >= minY) {
            for (let y = minY; y <= maxY; y++) {
                const row = y * width;
                // SPB-93 tools 2026-09-07: Add/Subtract can only change this
                // rectangle. Avoid scanning all16M pixels after a small4096px
                // selection; retain exact soft-mask comparisons and no-op counts.
                for (let x = minX; x <= maxX; x++) {
                    enclosedPixels++;
                    if (mode !== 'replace' && current[row + x] !== value) changedPixels++;
                }
                next.fill(value, row + minX, row + maxX + 1);
            }
        }
        return {
            nextMask: next,
            enclosedPixels,
            // Exact metadata belongs to this newly allocated hard Replace mask.
            // Add/Subtract can retain arbitrary old features outside this box.
            bounds: mode === 'replace' && enclosedPixels > 0
                ? { any: true, count: enclosedPixels, minX, minY, maxX, maxY } : null,
            changedPixels: mode === 'replace' ? countDifferences(current, next) : changedPixels,
        };
    }


    // PORT-W5 (2026-10-09, owner "tools basically SUCK"): feather the NEW rectangle only, via the PhotoCraft-ported selection
    // core (js/canvas/pc-selection-core.js, sigma = radius/2, no cap), then combine with the existing mask.  The previous
    // commit feathered the WHOLE accumulated mask, so every Add/Subtract re-blurred (and shrank) every earlier selection.
    // Hard rectangle edges stay hard (anti-alias off, like Photoshop) when feather is 0 - this is only called for feather > 0.
    function composeFeathered(currentMask, widthValue, heightValue, gestureValue, modeValue, featherValue) {
        const g = typeof window !== 'undefined' ? window : globalThis;
        let core = g.SPB_PC_W5_OFF || g.SPB_PC_W1_OFF ? null : g.SPBPcSelection;
        if (!core && !g.SPB_PC_W5_OFF && !g.SPB_PC_W1_OFF) { try { if (typeof require === 'function') core = require('../pc-selection-core.js'); } catch (e) { core = null; } }
        if (!core || !core.feather) return null;
        const width = Math.max(0, Math.floor(Number(widthValue) || 0));
        const height = Math.max(0, Math.floor(Number(heightValue) || 0));
        const r = Math.max(0, Math.min(1000, Number(featherValue) || 0));
        if (!r || !width || !height) return null;
        const gesture = gestureValue || {};
        const minX = Math.max(0, Math.min(width - 1, Math.floor(Number(gesture.x1) || 0)));
        const maxX = Math.max(0, Math.min(width - 1, Math.ceil(Number(gesture.x2) || 0) - (_tfx2Off() ? 0 : 1))); // [SPB-TFX2 TA-018] exclusive end
        const minY = Math.max(0, Math.min(height - 1, Math.floor(Number(gesture.y1) || 0)));
        const maxY = Math.max(0, Math.min(height - 1, Math.ceil(Number(gesture.y2) || 0) - (_tfx2Off() ? 0 : 1)));
        if (maxX < minX || maxY < minY) return null;
        // crop window = rect + 3 sigma (1.5 r) of padding; outside the canvas counts as unselected, exactly as in a full-canvas feather
        const pad = Math.ceil(r * 1.5) + 2;
        const cx0 = Math.max(0, minX - pad), cy0 = Math.max(0, minY - pad);
        const cx1 = Math.min(width, maxX + 1 + pad), cy1 = Math.min(height, maxY + 1 + pad);
        const cw = cx1 - cx0, ch = cy1 - cy0;
        // zero padding where the canvas has no pixels but the feather would have bled (canvas edge): same as full-canvas zero-outside
        const sub = new Uint8Array(cw * ch);
        for (let y = minY; y <= maxY; y++) sub.fill(255, (y - cy0) * cw + (minX - cx0), (y - cy0) * cw + (maxX - cx0) + 1);
        const soft = core.feather(sub, cw, ch, r);
        const mode = modeValue === 'subtract' || modeValue === 'replace' ? modeValue : 'add';
        const length = width * height;
        const current = currentMask instanceof Uint8Array && currentMask.length === length ? currentMask : new Uint8Array(length);
        const next = mode === 'replace' ? new Uint8Array(length) : new Uint8Array(current);
        for (let y = 0; y < ch; y++) {
            const row = (y + cy0) * width + cx0, srow = y * cw;
            for (let x = 0; x < cw; x++) {
                const f = soft[srow + x];
                if (!f) continue;
                const i = row + x;
                if (mode === 'subtract') next[i] = Math.round(current[i] * (255 - f) / 255);
                else next[i] = f > next[i] ? f : next[i];
            }
        }
        return next;
    }

    return { resolveGesture, validateGesture, dirtyRect, composeMask, composeFeathered, countDifferences };
});
