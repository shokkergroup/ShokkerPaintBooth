// SPB-93 tools 2026-09-07: bounded preview queue, one computation in flight.
// Never detach the authoritative source. Cancel/Apply terminate the session.
(function (root, factory) {
    const api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBAdjustmentWorker = api;
})(typeof window === 'object' ? window : globalThis, function (root) {
    'use strict';
    function create(options) {
        const WorkerType = options.WorkerType || root.Worker;
        if (!WorkerType || options.source.length < 4 * 1024 * 1024) return null;
        let worker;
        try { worker = new WorkerType('js/canvas/layer/adjustment-worker.js?v=spb-adjust-worker-20260907'); }
        catch (_) { return null; }
        let stopped = false, busy = false, pending = null, latest = null, sequence = 0, inFlight = 0;
        function dispose() {
            if (stopped) return;
            stopped = true; pending = null;
            worker.terminate();
        }
        function fail() {
            if (stopped) return;
            dispose();
            if (latest) options.onError(latest);
        }
        function pump() {
            if (stopped || busy || !pending) return;
            const values = pending; pending = null; busy = true;
            inFlight = ++sequence;
            try { worker.postMessage({ type: 'preview', id: inFlight, values }); }
            catch (_) { fail(); }
        }
        worker.onmessage = event => {
            if (stopped) return;
            const message = event.data;
            if (message.error) { fail(); return; }
            if (!busy || message.id !== inFlight) return;
            busy = false;
            try { options.onFrame(new Uint8ClampedArray(message.pixels)); }
            catch (_) { fail(); return; }
            pump();
        };
        worker.onerror = event => { if (event.preventDefault) event.preventDefault(); fail(); };
        try {
            const copy = new Uint8ClampedArray(options.source);
            worker.postMessage({ type: 'init', mutator: options.mutator, source: copy.buffer }, [copy.buffer]);
        } catch (_) { dispose(); return null; }
        return Object.freeze({
            request(values) {
                if (stopped) return false;
                latest = Array.from(values || []); pending = latest;
                pump();
                return true;
            },
            dispose
        });
    }
    return Object.freeze({ create });
});
