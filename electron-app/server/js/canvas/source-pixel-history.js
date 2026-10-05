// SPB-93 2026-09-07: pixel snapshots belong to the outgoing document.
// Preserve retained Zone history, including its chronological position.
(function(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBSourcePixelHistory = api;
})(typeof window === 'object' ? window : globalThis, function() {
    'use strict';
    const keys = ['undo', 'redo', 'undoTrail', 'redoTrail', 'view'];
    function capture(state) {
        return Object.fromEntries(keys.map(key => [key, Array.isArray(state[key]) ? state[key].slice() : null]));
    }
    function restore(state, snapshot) {
        if (!snapshot) return;
        for (const key of keys) if (Array.isArray(state[key]) && Array.isArray(snapshot[key])) {
            state[key].splice(0, state[key].length, ...snapshot[key]);
        }
    }
    function clear(state) {
        for (const key of ['undo', 'redo']) if (Array.isArray(state[key])) state[key].length = 0;
        const outgoing = kind => kind === 'pixel' || kind === 'layer';
        for (const key of ['undoTrail', 'redoTrail', 'view']) {
            const entries = state[key];
            if (!Array.isArray(entries)) continue;
            const kept = entries.filter(entry => !outgoing(key === 'view' ? entry?.kind : entry));
            entries.splice(0, entries.length, ...kept);
        }
    }
    return Object.freeze({ capture, restore, clear });
});
