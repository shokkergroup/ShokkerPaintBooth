(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSourceFileCommit = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // SPB-93 2026-09-07: direct imports share the source-path transaction.
    // Decode first; keep the outgoing document until pixels and masks publish.
    function run(deps, width, height, draw, clearPSD) {
        if (!deps.canvas || ![width, height].every(v => Number.isInteger(v) && v > 0)) {
            throw new Error('Invalid source canvas or dimensions');
        }
        deps.settle();
        const previous = deps.capture();
        try {
            const canvas = deps.canvas;
            deps.resizeMasks(canvas.width, canvas.height, width, height);
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext('2d', { willReadFrequently: true });
            draw(context);
            deps.publish(context.getImageData(0, 0, width, height));
            if (clearPSD !== false) deps.clearPSD();
        } catch (error) {
            deps.restore(previous);
            throw error;
        }
    }
    return { run };
});
