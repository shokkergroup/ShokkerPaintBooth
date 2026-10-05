/* SPB-93 2026-09-08: SOURCE and export must publish identical committed pixels.
   A reused display canvas rounded RGB by one after Transform/Undo while a
   fresh stack composite remained exact. Keep gesture previews independent. */
(function(root) {
    'use strict';
    function render(width, height, compose, createCanvas) {
        const canvas = createCanvas();
        canvas.width = width; canvas.height = height;
        const context = canvas.getContext('2d', { willReadFrequently: true });
        const result = compose(context);
        if (!result.ok) return { result };
        return { result, canvas, pixels: context.getImageData(0, 0, width, height) };
    }
    const api = { render };
    root.SPBLayerCompositePublication = api;
    if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
