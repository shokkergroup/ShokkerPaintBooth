(function (global) {
    'use strict';

    function clamp01(value) {
        return Math.max(0, Math.min(1, value));
    }

    function arraysDiffer(before, after) {
        if (!before || !after || before.length !== after.length) return true;
        for (let i = 0; i < before.length; i++) {
            if (before[i] !== after[i]) return true;
        }
        return false;
    }

    function constrainEndpoint(start, end, shouldSnap) {
        if (!start || !end || !shouldSnap) return end;
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const length = Math.hypot(dx, dy);
        if (!length) return end;
        const step = Math.PI / 4;
        const angle = Math.round(Math.atan2(dy, dx) / step) * step;
        return {
            x: start.x + Math.cos(angle) * length,
            y: start.y + Math.sin(angle) * length
        };
    }

    function dirtyRect(start, end, width, height, padding) {
        if (!start || !end || width <= 0 || height <= 0) return null;
        const pad = Math.max(1, Math.ceil(padding || 1));
        const x = Math.max(0, Math.floor(Math.min(start.x, end.x) - pad));
        const y = Math.max(0, Math.floor(Math.min(start.y, end.y) - pad));
        const right = Math.min(width, Math.ceil(Math.max(start.x, end.x) + pad + 1));
        const bottom = Math.min(height, Math.ceil(Math.max(start.y, end.y) + pad + 1));
        return right > x && bottom > y ? { x, y, width: right - x, height: bottom - y } : null;
    }

    // SPB-93 tick 18, owner verdict: tools still feel "jinky/off." The pure
    // kernel computes a complete candidate before the caller owns history.
    // Served before -> after: six-point drag 1089-1416ms -> 221ms Zone / 256ms
    // Layer; duplicate Replace needed two undos -> skip + one honest undo.
    function computeZoneMask(existingMask, width, height, x1, y1, x2, y2, type, reverse, selectionMode) {
        const pixelCount = Math.max(0, width * height);
        const current = existingMask && existingMask.length === pixelCount
            ? existingMask
            : new Uint8Array(pixelCount);
        const next = new Uint8Array(current);
        const dx = x2 - x1;
        const dy = y2 - y1;
        const length = Math.hypot(dx, dy);
        if (length < 2 || pixelCount === 0) return { mask: next, changed: false, valid: false };

        const nx = dx / length;
        const ny = dy / length;
        const angleReference = Math.atan2(dy, dx);
        const mode = selectionMode === 'replace' || selectionMode === 'subtract' ? selectionMode : 'add';
        const gradientType = type || 'linear';
        let changed = false;

        for (let py = 0; py < height; py++) {
            for (let px = 0; px < width; px++) {
                let t = 0;
                if (gradientType === 'linear') {
                    t = ((px - x1) * nx + (py - y1) * ny) / length;
                } else if (gradientType === 'radial') {
                    t = Math.hypot(px - x1, py - y1) / length;
                } else if (gradientType === 'angular') {
                    const angle = Math.atan2(py - y1, px - x1) - angleReference;
                    t = ((angle + Math.PI) / (2 * Math.PI)) % 1;
                } else if (gradientType === 'diamond') {
                    const along = Math.abs((px - x1) * nx + (py - y1) * ny) / length;
                    const across = Math.abs(-(px - x1) * ny + (py - y1) * nx) / length;
                    t = along + across;
                } else if (gradientType === 'reflected') {
                    t = Math.abs(((px - x1) * nx + (py - y1) * ny) / length);
                    t = t > 1 ? 2 - t : t;
                } else if (gradientType === 'spiral-cw' || gradientType === 'spiral-ccw') {
                    const angle = Math.atan2(py - y1, px - x1) - angleReference;
                    const distance = Math.hypot(px - x1, py - y1) / length;
                    const direction = gradientType === 'spiral-cw' ? 1 : -1;
                    t = ((direction * angle / (2 * Math.PI) + distance) % 1 + 1) % 1;
                } else if (gradientType === 'conical') {
                    const angle = Math.atan2(py - y1, px - x1) - angleReference;
                    t = ((angle / (2 * Math.PI)) % 1 + 1) % 1;
                }
                if (reverse) t = 1 - t;
                const value = Math.round((1 - clamp01(t)) * 255);
                const index = py * width + px;
                const oldValue = current[index];
                const nextValue = mode === 'replace'
                    ? value
                    : (mode === 'subtract' ? Math.max(0, oldValue - value) : Math.max(oldValue, value));
                next[index] = nextValue;
                if (nextValue !== oldValue) changed = true;
            }
        }
        return { mask: next, changed, valid: true };
    }

    const api = Object.freeze({ arraysDiffer, constrainEndpoint, dirtyRect, computeZoneMask });
    global.SPBGradient = api;
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
