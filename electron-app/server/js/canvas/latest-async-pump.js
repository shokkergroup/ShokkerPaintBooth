(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBLatestAsyncPump = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function create(worker, options) {
        if (typeof worker !== 'function') throw new TypeError('worker must be a function');
        const opts = options || {};
        const delayMs = Math.max(0, Number(opts.delayMs) || 0);
        let running = false;
        let queued = false;
        let timer = null;

        function schedule() {
            if (running || timer != null || !queued) return;
            timer = setTimeout(run, delayMs);
        }

        async function run() {
            timer = null;
            if (!queued || running) return;
            queued = false;
            running = true;
            try {
                await worker();
            } catch (error) {
                if (typeof opts.onError === 'function') opts.onError(error);
            } finally {
                running = false;
                schedule();
            }
        }

        function request() {
            queued = true;
            schedule();
            return true;
        }

        function cancelPending() {
            queued = false;
            if (timer != null) clearTimeout(timer);
            timer = null;
        }

        return Object.freeze({
            request,
            cancelPending,
            isRunning: function () { return running; },
            hasPending: function () { return queued || timer != null; },
        });
    }

    return Object.freeze({ create });
});
