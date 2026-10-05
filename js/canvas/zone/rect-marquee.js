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
        const maxX = Math.max(0, Math.min(width - 1, Math.ceil(Number(gesture.x2) || 0)));
        const minY = Math.max(0, Math.min(height - 1, Math.floor(Number(gesture.y1) || 0)));
        const maxY = Math.max(0, Math.min(height - 1, Math.ceil(Number(gesture.y2) || 0)));
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

    return { resolveGesture, validateGesture, dirtyRect, composeMask, countDifferences };
});
