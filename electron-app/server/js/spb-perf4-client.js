/* [PERF-4 2026-10-10] Warm a Material / Spec Brush coat's full-canvas render before the first stroke needs it.
 *
 * A studio coat's finish is rendered once on the full canvas by the server and memoised (engine/rev_material_layer.py); every later stroke of the same
 * finish + sliders is only a re-composite. The FIRST stroke of a slow finish pays that render inside its own preview (candy 4.4-5.2 s, terrazzo 5.8-8.7 s,
 * sequin 6.0 s on a loaded host). The render does not depend on the stroke, so the brush asks for it earlier: on Apply in the finish picker and on
 * pointer-down of a stroke (js/rev/material/rev-material-ui.js calls SPBPerf4.warm(SPBRevMaterial.warmZone(finish, params))).
 *
 * This file only (1) learns the preview seed + scale from the page's own /preview-render requests, so the warm renders at the size and seed the live
 * preview uses, and (2) POSTs the coat zone to /api/perf4/warm-coat (server_routes/perf4_warm_routes.py: idle-only, same engine call as a preview, a
 * running warm makes user requests wait instead of 429, they then hit the memo). Fire and forget; any failure leaves today's behaviour.
 * Kill switch: window.SPB_PERF4_OFF = true or localStorage.SPB_PERF4_OFF = '1' (page); env SPB_PERF4_OFF=1 (server).
 */
(function () {
    'use strict';
    if (typeof window === 'undefined' || window.__spbPerf4ClientInstalled) return;
    window.__spbPerf4ClientInstalled = true;

    var last = { scale: null, seed: 51 };
    var sent = new Map();   // dedupe key -> time of the last warm POST
    var stats = { posts: 0, dup: 0, noSource: 0, errors: 0, lastStatus: null };
    window.__spbPerf4Stats = stats;

    function isOff() {
        try { if (window.SPB_PERF4_OFF === true) return true; } catch (_) {}
        try { if (window.localStorage && localStorage.getItem('SPB_PERF4_OFF') === '1') return true; } catch (_) {}
        return false;
    }

    var origFetch = (typeof window.fetch === 'function') ? window.fetch.bind(window) : null;
    if (!origFetch) return;

    // learn seed + preview_scale from the page's own live preview requests (key order: ..., zones, seed, preview_scale, ...)
    window.fetch = function (input, init) {
        try {
            var url = (typeof input === 'string') ? input : ((input && input.url) || '');
            if (init && typeof init.body === 'string' && /\/preview-render(\?|$)/.test(url)) {
                var b = init.body, i = b.lastIndexOf('"preview_scale":');
                if (i > 0) {
                    var m = /^"preview_scale":\s*([0-9.]+)/.exec(b.slice(i, i + 40));
                    if (m) last.scale = parseFloat(m[1]);
                    var s = /"seed":\s*(-?\d+)\s*,\s*$/.exec(b.slice(Math.max(0, i - 40), i));
                    if (s) last.seed = parseInt(s[1], 10);
                }
            }
        } catch (_) {}
        return origFetch(input, init);
    };

    function token() {
        try { if (typeof _previewPaintSourceMemo !== 'undefined' && _previewPaintSourceMemo && _previewPaintSourceMemo.token) return _previewPaintSourceMemo.token; } catch (_) {}
        return null;
    }
    function zoneSig(z) {
        var o = {};
        Object.keys(z).forEach(function (k) { if (k !== 'region_mask' && k !== 'name' && k !== '_spb_rev_material') o[k] = z[k]; });
        return JSON.stringify(o);
    }
    /** Cheap pre-check (no work): a base for dedupe keys, or null when the page has no live preview source / scale yet. */
    function ready() {
        if (isOff() || last.scale == null) return null;
        var t = token();
        return t ? (t + '|' + last.seed + '|' + last.scale) : null;
    }
    /** pack = SPBRevMaterial.warmZone(...) -> {zone, size}. Returns true when a request was sent. */
    function warm(pack) {
        try {
            if (!pack || !pack.zone) return false;
            var base = ready();
            if (!base) { stats.noSource++; return false; }
            var key = base + '|' + zoneSig(pack.zone), now = Date.now(), t = sent.get(key);
            if (t && now - t < 120000) { stats.dup++; return false; }
            if (sent.size > 64) sent.clear();
            sent.set(key, now);
            var api = (window.ShokkerAPI && ShokkerAPI.baseUrl) || '';
            stats.posts++;
            origFetch(api + '/api/perf4/warm-coat', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ coat: pack.zone, size: pack.size, seed: last.seed, preview_scale: last.scale, paint_source_token: token() })
            }).then(function (r) { return r.json(); }).then(function (j) { stats.lastStatus = j && j.status; })
              .catch(function () { stats.errors++; });
            return true;
        } catch (_) { stats.errors++; return false; }
    }
    window.SPBPerf4 = { warm: warm, ready: ready, stats: stats, state: last };
})();
