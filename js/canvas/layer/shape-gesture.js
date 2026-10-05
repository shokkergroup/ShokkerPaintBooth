(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBShapeGesture = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const LINE_TYPES = new Set(['line', 'arrow']);

    function point(value) {
        return {
            x: Number.isFinite(Number(value && value.x)) ? Number(value.x) : 0,
            y: Number.isFinite(Number(value && value.y)) ? Number(value.y) : 0,
        };
    }

    function isLineType(shapeType) {
        return LINE_TYPES.has(String(shapeType || '').toLowerCase());
    }

    // SPB-93 tick 19, owner verdict: tools still feel "jinky/off." Keep one
    // pure gesture contract for preview and commit. Served baseline: Shift on a
    // horizontal Line forced a diagonal; Alt-from-center did not exist. Served
    // after: the same Shift drag stayed horizontal, Alt created a centered Shape
    // layer, and both preview and commit use this exact endpoint contract.
    function resolveGesture(anchorValue, pointerValue, shapeType, options) {
        const anchor = point(anchorValue);
        const pointer = point(pointerValue);
        const opts = options || {};
        let dx = pointer.x - anchor.x;
        let dy = pointer.y - anchor.y;

        if (opts.shiftKey) {
            if (isLineType(shapeType)) {
                const length = Math.hypot(dx, dy);
                if (length > 0) {
                    const step = Math.PI / 4;
                    const angle = Math.round(Math.atan2(dy, dx) / step) * step;
                    dx = Math.cos(angle) * length;
                    dy = Math.sin(angle) * length;
                }
            } else {
                const size = Math.max(Math.abs(dx), Math.abs(dy));
                dx = size * Math.sign(dx || 1);
                dy = size * Math.sign(dy || 1);
            }
        }

        if (opts.altKey) {
            return {
                start: { x: anchor.x - dx, y: anchor.y - dy },
                end: { x: anchor.x + dx, y: anchor.y + dy },
            };
        }
        return {
            start: anchor,
            end: { x: anchor.x + dx, y: anchor.y + dy },
        };
    }

    function validateGesture(startValue, endValue, shapeType, options) {
        const start = point(startValue);
        const end = point(endValue);
        const opts = options || {};
        const strokeWidth = Math.max(0, Number(opts.strokeWidth) || 0);
        const filled = opts.filled === true;
        const minSize = Math.max(1, Number(opts.minSize) || 2);
        const width = Math.abs(end.x - start.x);
        const height = Math.abs(end.y - start.y);

        if (isLineType(shapeType)) {
            if (strokeWidth <= 0) {
                return { valid: false, reason: 'Shape Line needs a Stroke width above 0' };
            }
            if (Math.hypot(width, height) < minSize) {
                return { valid: false, reason: 'Shape: drag farther to draw a visible line' };
            }
        } else {
            if (!filled && strokeWidth <= 0) {
                return { valid: false, reason: 'Shape needs Fill or a Stroke width above 0' };
            }
            if (width < minSize || height < minSize) {
                return { valid: false, reason: 'Shape: click and drag to set width and height' };
            }
        }
        return { valid: true, width, height };
    }

    function polygonRadius(startValue, endValue) {
        const start = point(startValue);
        const end = point(endValue);
        return Math.min(Math.abs(end.x - start.x), Math.abs(end.y - start.y)) / 2;
    }

    function dirtyRect(startValue, endValue, width, height, strokeWidth, shapeType) {
        const start = point(startValue);
        const end = point(endValue);
        const canvasWidth = Math.max(0, Math.floor(Number(width) || 0));
        const canvasHeight = Math.max(0, Math.floor(Number(height) || 0));
        const stroke = Math.max(0, Number(strokeWidth) || 0);
        const pad = isLineType(shapeType)
            ? Math.max(12, Math.ceil(stroke * 4 + 4))
            : Math.max(4, Math.ceil(stroke / 2 + 3));
        const x = Math.max(0, Math.floor(Math.min(start.x, end.x) - pad));
        const y = Math.max(0, Math.floor(Math.min(start.y, end.y) - pad));
        const right = Math.min(canvasWidth, Math.ceil(Math.max(start.x, end.x) + pad + 1));
        const bottom = Math.min(canvasHeight, Math.ceil(Math.max(start.y, end.y) + pad + 1));
        return right > x && bottom > y
            ? { x, y, width: right - x, height: bottom - y }
            : null;
    }

    return {
        dirtyRect,
        isLineType,
        point,
        polygonRadius,
        resolveGesture,
        validateGesture,
    };
});
