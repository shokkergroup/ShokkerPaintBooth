// SPB-93 2026-09-07: repaint the union of uploaded brush pixels while keeping
// the authoritative stack compositor, blend modes and full-command fallback.
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPaintPreviewRegion = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    function createQueue() {
        let full = false, bounds = null;
        function clear() { full = false; bounds = null; }
        return {
            add(rect) {
                if (!rect || ![rect.x, rect.y, rect.width, rect.height].every(Number.isFinite)
                    || rect.width <= 0 || rect.height <= 0) { full = true; bounds = null; return; }
                if (full) return;
                const right = rect.x + rect.width, bottom = rect.y + rect.height;
                bounds = bounds ? { x: Math.min(bounds.x, rect.x), y: Math.min(bounds.y, rect.y),
                    right: Math.max(bounds.right, right), bottom: Math.max(bounds.bottom, bottom) }
                    : { x: rect.x, y: rect.y, right, bottom };
            },
            consume() {
                const region = !full && bounds ? { x: bounds.x, y: bounds.y,
                    width: bounds.right - bounds.x, height: bounds.bottom - bounds.y } : null;
                clear(); return region;
            }, clear
        };
    }
    function paint(ctx, region, draw) {
        ctx.save();
        try {
            if (region) {
                ctx.beginPath(); ctx.rect(region.x, region.y, region.width, region.height); ctx.clip();
            }
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            return draw();
        } finally { ctx.restore(); }
    }
    return Object.freeze({ createQueue, paint });
});
