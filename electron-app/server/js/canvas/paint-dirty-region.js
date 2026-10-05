(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPaintDirtyRegion = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function create(widthValue, heightValue) {
        const width = Math.max(0, Math.floor(Number(widthValue) || 0));
        const height = Math.max(0, Math.floor(Number(heightValue) || 0));
        let bounds = null;

        function addRect(xValue, yValue, widthValue, heightValue) {
            const x0 = Math.max(0, Math.floor(Number(xValue) || 0));
            const y0 = Math.max(0, Math.floor(Number(yValue) || 0));
            const x1 = Math.min(width, Math.ceil((Number(xValue) || 0) + Math.max(0, Number(widthValue) || 0)));
            const y1 = Math.min(height, Math.ceil((Number(yValue) || 0) + Math.max(0, Number(heightValue) || 0)));
            if (x1 <= x0 || y1 <= y0) return false;
            if (!bounds) bounds = { x0, y0, x1, y1 };
            else {
                bounds.x0 = Math.min(bounds.x0, x0);
                bounds.y0 = Math.min(bounds.y0, y0);
                bounds.x1 = Math.max(bounds.x1, x1);
                bounds.y1 = Math.max(bounds.y1, y1);
            }
            return true;
        }

        function addCircle(xValue, yValue, radiusValue, paddingValue) {
            const x = Number(xValue) || 0;
            const y = Number(yValue) || 0;
            const radius = Math.max(0, Number(radiusValue) || 0);
            const padding = Math.max(0, Number(paddingValue) || 0);
            const outer = radius + padding;
            return addRect(x - outer, y - outer, outer * 2 + 1, outer * 2 + 1);
        }

        function consume() {
            if (!bounds) return null;
            const result = {
                x: bounds.x0,
                y: bounds.y0,
                width: bounds.x1 - bounds.x0,
                height: bounds.y1 - bounds.y0,
            };
            bounds = null;
            return result;
        }

        return Object.freeze({ addRect, addCircle, consume, clear: function () { bounds = null; } });
    }

    return Object.freeze({ create });
});
