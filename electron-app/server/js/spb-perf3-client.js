/* [PERF-3 2026-10-10] Live Preview: send unchanged layer payloads by reference.
 *
 * PERF-2 capture (owner car, 5-8 zones): every /preview-render POST carried 3.7-8.2 MB, ~85 % of
 * it the per-zone `source_layer_rgb_png` (base64 PNG of the restricted layers) and
 * `source_layer_mask` (RLE) that had not changed since the previous request. This wrapper
 * replaces each such payload with `<field>_ref: sha256(payload text)` once the server holds it
 * (server.py _perf3_resolve_payload_refs stores every full payload of a `perf3_refs` request
 * under the sha256 IT computes, and resolves refs before anything reads the body, keeping the
 * zone's key order). Unknown ref -> 409 perf3_need_payloads -> this wrapper re-sends the full
 * body once and the caller never sees the 409. Output pixels are identical by construction
 * (ON/OFF hashes in _easy_claude_work/perf2/PERF3_PROGRESS.md).
 * Kill switch: window.SPB_PERF3_OFF = true or localStorage.SPB_PERF3_OFF = '1' (page);
 * env SPB_PERF3_OFF=1 (server; the page then falls back to full bodies for 2 min at a time).
 */
(function () {
    'use strict';
    if (typeof window === 'undefined' || window.__spbPerf3ClientInstalled) return;
    if (typeof window.fetch !== 'function') return;
    window.__spbPerf3ClientInstalled = true;

    var FIELDS = ['source_layer_mask', 'source_layer_rgb_png'];
    var MIN_BODY = 100000;
    var held = new Set();        // sha256 keys the server stored (200 after a perf3_refs upload)
    var keyByText = new Map();   // payload text -> sha256 hex (bounded)
    var misses = new Map();      // key -> 409 count; a key the server keeps not resolving stops being sent by ref
    var disabledUntil = 0;
    var stats = { posts: 0, lean: 0, refs: 0, bytesFull: 0, bytesSent: 0, retries: 0, serverOff: 0, errors: 0 };
    window.__spbPerf3Stats = stats;

    function isOff() {
        try { if (window.SPB_PERF3_OFF === true) return true; } catch (_) {}
        try { if (window.localStorage && localStorage.getItem('SPB_PERF3_OFF') === '1') return true; } catch (_) {}
        return false;
    }

    async function sha256Hex(text) {
        var k = keyByText.get(text);
        if (k) return k;
        var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
        var b = new Uint8Array(buf);
        var hex = '';
        for (var i = 0; i < b.length; i++) hex += (b[i] < 16 ? '0' : '') + b[i].toString(16);
        if (keyByText.size > 96) keyByText.clear();
        keyByText.set(text, hex);
        return hex;
    }

    var origFetch = window.fetch.bind(window);

    async function perf3Fetch(input, init) {
        var url = (typeof input === 'string') ? input : ((input && input.url) || '');
        if (!init || typeof init.body !== 'string' || init.body.length < MIN_BODY
            || !/\/preview-render(\?|$)/.test(url)
            || String(init.method || 'GET').toUpperCase() !== 'POST'
            || isOff() || Date.now() < disabledUntil
            || !(window.crypto && crypto.subtle && typeof TextEncoder === 'function')
            || init.body.charAt(0) !== '{' || init.body.charAt(1) === '}') {
            return origFetch(input, init);
        }
        var prep;
        try { prep = await prepare(init.body); } catch (_) { stats.errors++; prep = null; }
        if (!prep) return origFetch(input, init);
        var keys = prep.keys, usedRef = prep.usedRef, fullText = prep.fullText, sendText = prep.sendText;
        stats.bytesFull += init.body.length;
        stats.bytesSent += sendText.length;
        var resp = await origFetch(input, Object.assign({}, init, { body: sendText }));
        if (resp.status === 409 && usedRef) {
            var j = null;
            try { j = await resp.clone().json(); } catch (_) {}
            if (j && j.error === 'perf3_need_payloads') {
                stats.retries++;
                held.clear();
                (Array.isArray(j.missing) ? j.missing : []).forEach(function (m) {
                    var k = prep.refAt[String(m)];
                    if (k) misses.set(k, (misses.get(k) || 0) + 1);
                });
                if (j.perf3 === 'off') {
                    stats.serverOff++;
                    disabledUntil = Date.now() + 120000;
                    return origFetch(input, init);
                }
                stats.bytesSent += fullText.length;
                resp = await origFetch(input, Object.assign({}, init, { body: fullText }));
            }
        }
        if (resp.ok) {
            for (var ki = 0; ki < keys.length; ki++) held.add(keys[ki]);
            if (held.size > 256) held.clear();
        }
        return resp;
    }

    async function prepare(rawBody) {
        var body = JSON.parse(rawBody);
        if (!body || typeof body !== 'object' || !Array.isArray(body.zones)) return null;
        stats.posts++;
        var keys = [];
        var refAt = {};
        var usedRef = false;
        var leanZones = [];
        for (var zi = 0; zi < body.zones.length; zi++) {
            var z = body.zones[zi];
            if (!z || typeof z !== 'object' || Array.isArray(z)) { leanZones.push(z); continue; }
            var repl = null;
            for (var fi = 0; fi < FIELDS.length; fi++) {
                var f = FIELDS[fi];
                var v = z[f];
                if (v === undefined || v === null) continue;
                var text = (typeof v === 'string') ? v : JSON.stringify(v);
                var key = await sha256Hex(text);
                keys.push(key);
                if (held.has(key) && (misses.get(key) || 0) < 2) {
                    (repl || (repl = {}))[f] = key;
                    refAt[zi + ':' + f] = key;
                    stats.refs++;
                }
            }
            if (!repl) { leanZones.push(z); continue; }
            usedRef = true;
            // Same key ORDER as the full zone: "<field>" becomes "<field>_ref" in place.
            var lz = {};
            Object.keys(z).forEach(function (k) {
                if (Object.prototype.hasOwnProperty.call(repl, k)) lz[k + '_ref'] = repl[k];
                else lz[k] = z[k];
            });
            leanZones.push(lz);
        }
        // Full body + store flag: spliced in front so every other byte is the caller's own text.
        var fullText = '{"perf3_refs":1,' + rawBody.slice(1);
        var sendText = fullText;
        if (usedRef) {
            var lean = {};
            lean.perf3_refs = 1;
            Object.keys(body).forEach(function (k) { if (k !== 'perf3_refs') lean[k] = (k === 'zones') ? leanZones : body[k]; });
            sendText = JSON.stringify(lean);
            stats.lean++;
        }
        return { keys: keys, refAt: refAt, usedRef: usedRef, fullText: fullText, sendText: sendText };
    }

    window.fetch = function (input, init) {
        try {
            return perf3Fetch(input, init);
        } catch (err) {
            stats.errors++;
            return origFetch(input, init);
        }
    };
    window.fetch.__spbPerf3 = true;
})();
