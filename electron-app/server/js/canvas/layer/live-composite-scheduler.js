(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLayerLiveComposite = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    function create(options) {
        const opts = options || {};
        const requestFrame = opts.requestFrame || root.requestAnimationFrame.bind(root);
        const cancelFrame = opts.cancelFrame || root.cancelAnimationFrame.bind(root);
        let frameId = null;
        let pendingRender = null;

        function runPending() {
            frameId = null;
            const render = pendingRender;
            pendingRender = null;
            if (typeof render === 'function') render();
        }

        function request(render) {
            if (typeof render !== 'function') return false;
            pendingRender = render;
            if (frameId == null) frameId = requestFrame(runPending);
            return true;
        }

        function cancel() {
            if (frameId != null) cancelFrame(frameId);
            frameId = null;
            pendingRender = null;
        }

        function flush() {
            if (frameId != null) cancelFrame(frameId);
            frameId = null;
            const render = pendingRender;
            pendingRender = null;
            if (typeof render !== 'function') return false;
            render();
            return true;
        }

        return Object.freeze({ request, cancel, flush, isPending: function () { return frameId != null; } });
    }

    return Object.freeze({ create });
});
