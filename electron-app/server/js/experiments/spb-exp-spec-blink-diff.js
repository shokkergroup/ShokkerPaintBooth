/* ============================================================================
 * SPB EXPERIMENT — SPEC BLINK DIFF (spb-exp-spec-blink-diff.js)
 * ----------------------------------------------------------------------------
 * "Blink your last two renders like an astronomer hunting comets and see
 *  EXACTLY which panels your slider tweak changed in the metal."
 *
 * Extends the SPB-RECENTS-001 render-recall system (last-10 renders persisted
 * to disk with paint.png + spec.png + recipe.json):
 *   - list route:    GET  /recent-renders/list   (server_routes/render_file_routes.py:295)
 *   - file route:    GET  /recent-renders/<slot>/<file>            (…:330)
 *   - writer:        saveRecentRenderToDisk      (paint-booth-5-api-render.js:5454)
 *   - stock panel:   openRecentRendersPanel      (paint-booth-5-api-render.js:5480)
 *   - full restore:  restoreRecipeFromRecent     (paint-booth-5-api-render.js:5543)
 *   - zone installer fallback: window.spbApplyZones (paint-booth-5-api-render.js:5435)
 *
 * Pick renders A (default: latest) and B (default: previous). Two views:
 *   1) classic 2 Hz blink alternation of the two spec.pngs;
 *   2) |Δ| heat overlay per channel, with M / R / Cc chips wearing the channel
 *      dock's Photoshop-true tints (SPEC_DOCK_TINTS = r:[1,0,0] g:[0,1,0]
 *      b:[0,0,1], paint-booth-2-state-zones.js:3912).
 *
 * Per-zone impact clips the delta to each CURRENT zone's regionMask — the same
 * canvas-res masks the render payload encodes (_encodeZoneApplyMasks,
 * paint-booth-5-api-render.js:33-45) and the same clipping precedent as the
 * Spec Stats panel (paint-booth-2-state-zones.js:4246-4258) — then runs the
 * proven DOM-free stats core SPB_SpecStats.computeZoneSpecStats
 * (paint-booth-specstats.js:124) on BOTH frames to emit honest sentences like
 * "Hood: Clearcoat 112 → 38 (satin clear → gloss clear) — 61% of pixels moved."
 *
 * HONESTY GUARD: recipe.json's zoneSnapshot deliberately drops regionMask
 * (writer at paint-booth-5-api-render.js:3736-3746 skips heavy buffers), so
 * per-zone clipping is only trustworthy when the CURRENT zone layout matches
 * BOTH recipes' zoneSnapshots (compared by zone count + names + useRegion).
 * On mismatch we fall back to whole-livery stats and say so.
 *
 * CONTRACT (experiments registry):
 *   window.SPB_EXPERIMENTS.push({ id, name, pitch, enable(), disable() })
 *   - complete NO-OP until enable() is called (module top level only registers);
 *   - disable() removes every DOM node / listener / timer this module created.
 *
 * All app globals are driven defensively (typeof / try-catch guards): zones,
 * selectedZoneIndex, ShokkerAPI, showToast, SPB_SpecStats, MONOLITHICS,
 * restoreRecipeFromRecent, spbApplyZones, triggerPreviewRender.
 * Read-only toward the render pipeline: this tool never authors a spec.
 * ========================================================================== */
(function () {
    'use strict';

    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (window.__SPB_EXP_BLINK_DIFF_LOADED) return;
    window.__SPB_EXP_BLINK_DIFF_LOADED = true;

    // ---------------------------------------------------------------- consts
    var EXP_ID = 'spec-blink-diff';
    var EXP_NAME = 'Spec Blink Diff';
    var EXP_PITCH =
        'Blink your last two renders like an astronomer hunting comets and see ' +
        'EXACTLY which panels your slider tweak changed in the metal — because ' +
        'the spec never shows its work until now.';

    var STYLE_ID = 'spbExpBlinkStyle';
    var OVERLAY_ID = 'spbExpBlinkOverlay';
    var FLOAT_BTN_ID = 'spbExpBlinkFloatBtn';
    var EXP_MENU_ID = 'spbExperimentalMenu';      // js/features/experimental-menu.js:33

    var MOVED_T = 6;      // |Δ| levels (of 255) for a pixel to count as "moved"
    var MEDIAN_T = 4;     // per-channel median shift worth a sentence
    var BLINK_MS_DEFAULT = 500;   // 2 Hz alternation (astronomer default)

    // Photoshop-true channel hues — mirrors SPEC_DOCK_TINTS
    // (paint-booth-2-state-zones.js:3912; owner: "match Photoshop. Period.")
    var TINTS = { m: [1, 0, 0], r: [0, 1, 0], c: [0, 0, 1] };
    var CH_IDX = { m: 0, r: 1, c: 2 };
    var CH_NAME = { m: 'Metallic', r: 'Roughness', c: 'Clearcoat' };

    // ----------------------------------------------------------------- state
    var st = {
        enabled: false,
        open: false,
        listeners: [],        // [target, event, fn, opts] — removed on disable
        menuBtn: null,
        floatBtn: null,
        renders: [],          // /recent-renders/list payload (newest first)
        aIdx: -1,             // A = "after"  (newer)
        bIdx: -1,             // B = "before" (older)
        w: 0, h: 0,
        aData: null,          // ImageData of A's spec.png
        bData: null,          // ImageData of B's spec.png
        resampled: false,     // true when B had different dims and was rescaled
        frameCache: {},       // 'a:all' / 'b:m' / 'd:c:4' … -> canvas
        view: 'blink',        // 'blink' | 'delta'
        channel: 'all',       // 'all' | 'm' | 'r' | 'c'
        gain: 4,              // delta amplification
        blinkMs: BLINK_MS_DEFAULT,
        blinkTimer: null,
        showA: true,
        impactSeq: 0          // cancels stale async impact builds
    };

    // --------------------------------------------------------------- helpers
    function apiBase() {
        // Same origin logic as the app (ShokkerAPI.baseUrl, paint-booth-5-api-render.js:1513).
        try {
            if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && ShokkerAPI.baseUrl) {
                return ShokkerAPI.baseUrl;
            }
        } catch (_) { /* TDZ / not loaded yet */ }
        if (window.location && window.location.protocol === 'http:' && window.location.origin) {
            return window.location.origin;
        }
        return 'http://localhost:5001';
    }

    function toast(msg, isErr) {
        try {
            if (typeof showToast === 'function') { showToast(msg, !!isErr); return; }
        } catch (_) { }
        try { console[isErr ? 'warn' : 'log']('[spec-blink-diff] ' + msg); } catch (_) { }
    }

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function on(target, ev, fn, opts) {
        target.addEventListener(ev, fn, opts);
        st.listeners.push([target, ev, fn, opts]);
    }
    function offAll() {
        for (var i = 0; i < st.listeners.length; i++) {
            var l = st.listeners[i];
            try { l[0].removeEventListener(l[1], l[2], l[3]); } catch (_) { }
        }
        st.listeners = [];
    }

    function liveZones() {
        // `let zones` is a top-level lexical binding (paint-booth-2-state-zones.js:200):
        // reachable from other classic scripts by bare identifier, NOT via window.zones.
        try {
            if (typeof zones !== 'undefined' && Array.isArray(zones)) return zones;
        } catch (_) { }
        return null;
    }

    function statsCore() {
        try {
            if (typeof SPB_SpecStats !== 'undefined' && SPB_SpecStats &&
                typeof SPB_SpecStats.computeZoneSpecStats === 'function') {
                return SPB_SpecStats;
            }
        } catch (_) { }
        return null;
    }

    function chLabel(ch, v) {
        var core = statsCore();
        try {
            if (core) {
                if (ch === 'm' && core.metallicLabel) return core.metallicLabel(v);
                if (ch === 'r' && core.roughnessLabel) return core.roughnessLabel(v);
                if (ch === 'c' && core.clearcoatLabel) return core.clearcoatLabel(v);
            }
        } catch (_) { }
        return '';
    }

    function monolithicName(id) {
        try {
            if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) {
                for (var i = 0; i < MONOLITHICS.length; i++) {
                    if (MONOLITHICS[i] && MONOLITHICS[i].id === id) return MONOLITHICS[i].name || id;
                }
            }
        } catch (_) { }
        return id;
    }

    function finishSwatchUrl(id) {
        // Server-baked neutral swatch — same endpoint the zone list uses
        // (paint-booth-2-state-zones.js:5183).
        return apiBase() + '/api/swatch/monolithic/' + encodeURIComponent(id) +
            '?color=888888&size=48&prefer=live&v=spb-exp-blink';
    }

    // ------------------------------------------------------------------ CSS
    // Identical to css/experiments/spb-exp-spec-blink-diff.css; injected only
    // when that stylesheet is not linked, so either integration path works.
    var CSS_TEXT = '' +
        '.spb-exp-blink-overlay{position:fixed;inset:0;z-index:100060;background:rgba(2,4,10,.74);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;}' +
        '.spb-exp-blink-card{width:min(1080px,96vw);max-height:92vh;display:flex;flex-direction:column;background:#0d0d16;border:2px solid #7a5cff;border-radius:12px;box-shadow:0 24px 80px rgba(0,0,0,.72);overflow:hidden;}' +
        '.spb-exp-blink-header{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--border,#2a2a4a);}' +
        '.spb-exp-blink-header h3{margin:0;font-size:13px;letter-spacing:1px;color:#b9a4ff;}' +
        '.spb-exp-blink-header .spb-exp-blink-spacer{flex:1 1 auto;}' +
        '.spb-exp-blink-body{padding:12px;overflow:auto;display:flex;flex-direction:column;gap:10px;}' +
        '.spb-exp-blink-strip{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;}' +
        '.spb-exp-blink-pick{flex:0 0 auto;width:136px;background:var(--bg-card,#14142a);border:1px solid var(--border,#2a2a4a);border-radius:8px;padding:6px;display:flex;flex-direction:column;gap:4px;font-size:9px;color:var(--text,#c8cce0);position:relative;}' +
        '.spb-exp-blink-pick img{width:100%;aspect-ratio:1/1;object-fit:contain;background:#000;border-radius:4px;border:1px solid var(--border,#2a2a4a);}' +
        '.spb-exp-blink-pick.is-a{border-color:var(--accent-gold,#ffb000);}' +
        '.spb-exp-blink-pick.is-b{border-color:var(--accent-blue,#3366ff);}' +
        '.spb-exp-blink-pick .spb-exp-blink-when{color:var(--text-dim,#6b7787);}' +
        '.spb-exp-blink-pick .spb-exp-blink-summary{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
        '.spb-exp-blink-pick .spb-exp-blink-abtag{position:absolute;top:10px;left:10px;font-size:10px;font-weight:800;padding:1px 7px;border-radius:4px;background:rgba(0,0,0,.72);pointer-events:none;}' +
        '.spb-exp-blink-pick.is-a .spb-exp-blink-abtag{color:var(--accent-gold,#ffb000);}' +
        '.spb-exp-blink-pick.is-b .spb-exp-blink-abtag{color:#6da3ff;}' +
        '.spb-exp-blink-pickbtns{display:flex;gap:4px;}' +
        '.spb-exp-blink-pickbtns button{flex:1 1 0;font-size:10px;font-weight:700;padding:2px 0;border-radius:4px;border:1px solid var(--border,#2a2a4a);background:#08080f;color:var(--text,#c8cce0);cursor:pointer;}' +
        '.spb-exp-blink-pickbtns button.active-a{background:var(--accent-gold,#ffb000);border-color:var(--accent-gold,#ffb000);color:#0a0a14;}' +
        '.spb-exp-blink-pickbtns button.active-b{background:var(--accent-blue,#3366ff);border-color:var(--accent-blue,#3366ff);color:#fff;}' +
        '.spb-exp-blink-pickbtns button[disabled]{opacity:.35;cursor:not-allowed;}' +
        '.spb-exp-blink-chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:10px;color:var(--text-dim,#6b7787);}' +
        '.spb-exp-blink-chips .spb-exp-blink-chiplabel{font-size:9px;letter-spacing:.8px;text-transform:uppercase;margin-left:6px;}' +
        '.spb-exp-blink-chip{font-size:10px;font-weight:700;padding:3px 10px;border-radius:12px;border:1px solid var(--border,#2a2a4a);background:#08080f;color:var(--text,#c8cce0);cursor:pointer;}' +
        '.spb-exp-blink-chip.active{background:#b9a4ff;border-color:#b9a4ff;color:#0a0a14;}' +
        '.spb-exp-blink-chip[data-ch="m"].active{background:#ff5252;border-color:#ff5252;color:#0a0a14;}' +
        '.spb-exp-blink-chip[data-ch="r"].active{background:#4dff7a;border-color:#4dff7a;color:#0a0a14;}' +
        '.spb-exp-blink-chip[data-ch="c"].active{background:#5c8aff;border-color:#5c8aff;color:#0a0a14;}' +
        '.spb-exp-blink-viewwrap{position:relative;background:#05050b;border:1px solid var(--border,#2a2a4a);border-radius:8px;display:flex;align-items:center;justify-content:center;min-height:280px;overflow:hidden;}' +
        '.spb-exp-blink-canvas{max-width:100%;max-height:56vh;display:block;}' +
        '.spb-exp-blink-badge{position:absolute;top:8px;left:8px;font-size:11px;font-weight:800;letter-spacing:.8px;padding:2px 9px;border-radius:4px;background:rgba(0,0,0,.68);color:var(--accent-gold,#ffb000);pointer-events:none;}' +
        '.spb-exp-blink-badge.is-b{color:#6da3ff;}' +
        '.spb-exp-blink-badge.is-delta{color:#b9a4ff;}' +
        '.spb-exp-blink-readout{position:absolute;bottom:8px;left:8px;font-size:10px;font-family:ui-monospace,Consolas,monospace;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,.68);color:var(--text,#c8cce0);pointer-events:none;display:none;white-space:nowrap;}' +
        '.spb-exp-blink-status{font-size:11px;color:var(--text-dim,#6b7787);}' +
        '.spb-exp-blink-status.is-error{color:#ff6b6b;}' +
        '.spb-exp-blink-impact{display:flex;flex-direction:column;gap:4px;}' +
        '.spb-exp-blink-impact-head{font-size:10px;font-weight:800;letter-spacing:.8px;color:#b9a4ff;text-transform:uppercase;}' +
        '.spb-exp-blink-impact-note{font-size:10px;color:var(--text-dim,#6b7787);}' +
        '.spb-exp-blink-impact-row{display:flex;gap:8px;align-items:center;background:var(--bg-card,#14142a);border:1px solid var(--border,#2a2a4a);border-radius:6px;padding:5px 8px;font-size:11px;color:var(--text,#c8cce0);}' +
        '.spb-exp-blink-impact-row img.spb-exp-blink-swatch{width:22px;height:22px;border-radius:4px;flex:0 0 auto;border:1px solid rgba(255,255,255,.25);background:#000;object-fit:cover;}' +
        '.spb-exp-blink-impact-zone{font-weight:700;color:var(--text-bright,#e8ecff);min-width:90px;flex:0 0 auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
        '.spb-exp-blink-impact-text{flex:1 1 auto;min-width:0;}' +
        '.spb-exp-blink-impact-pct{flex:0 0 auto;font-weight:800;color:var(--accent-gold,#ffb000);}' +
        '.spb-exp-blink-impact-pct.is-quiet{color:var(--text-dim,#6b7787);}' +
        '.spb-exp-blink-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}' +
        '.spb-exp-blink-revert{border-color:var(--success,#00ff88)!important;color:var(--success,#00ff88)!important;}' +
        '.spb-exp-blink-revert[disabled]{opacity:.4;cursor:not-allowed;}' +
        '.spb-exp-blink-float{position:fixed;right:14px;bottom:14px;z-index:9500;font-size:11px;font-weight:700;letter-spacing:.4px;padding:6px 12px;border-radius:16px;cursor:pointer;background:rgba(122,92,255,.14);color:#b9a4ff;border:1px solid rgba(122,92,255,.55);box-shadow:0 6px 18px rgba(0,0,0,.5);}' +
        '.spb-exp-blink-float:hover{background:rgba(122,92,255,.28);}';

    function injectStyle() {
        if (document.getElementById(STYLE_ID)) return;
        // If the real stylesheet was linked by the integrator, don't duplicate.
        var links = document.querySelectorAll('link[rel="stylesheet"]');
        for (var i = 0; i < links.length; i++) {
            if (links[i].href && links[i].href.indexOf('spb-exp-spec-blink-diff') !== -1) return;
        }
        var style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = CSS_TEXT;
        (document.head || document.documentElement).appendChild(style);
    }
    function removeStyle() {
        var s = document.getElementById(STYLE_ID);
        if (s) s.remove();
    }

    // ------------------------------------------------------------- launchers
    function addLaunchers() {
        if (!st.enabled) return;
        if (document.readyState === 'loading') {
            on(document, 'DOMContentLoaded', addLaunchers, { once: true });
            return;
        }
        // Preferred anchor: the Experimental Features dropdown
        // (js/features/experimental-menu.js builds #spbExperimentalMenu > .spb-tb-pop
        // with .vtool-btn rows — we append one more row in the same shape).
        var pop = document.querySelector('#' + EXP_MENU_ID + ' .spb-tb-pop');
        if (pop && !st.menuBtn) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'vtool-btn';
            btn.title = 'Spec Blink Diff — blink renders A/B and heat-map exactly what changed in the spec map';
            btn.setAttribute('aria-label', EXP_NAME);
            var ico = document.createElement('span');
            ico.className = 'spb-mi-ico';
            ico.textContent = '🔭';
            btn.appendChild(ico);
            btn.appendChild(document.createTextNode(' Spec Blink Diff'));
            on(btn, 'click', function () {
                openPanel();
                var d = document.getElementById(EXP_MENU_ID);
                if (d) d.removeAttribute('open');
            });
            pop.appendChild(btn);
            st.menuBtn = btn;
            return;
        }
        // Fallback: small floating pill (only when the menu doesn't exist).
        if (!st.menuBtn && !document.getElementById(FLOAT_BTN_ID)) {
            var fb = document.createElement('button');
            fb.type = 'button';
            fb.id = FLOAT_BTN_ID;
            fb.className = 'spb-exp-blink-float';
            fb.title = 'Spec Blink Diff (experimental)';
            fb.textContent = '🔭 Blink Diff';
            on(fb, 'click', openPanel);
            document.body.appendChild(fb);
            st.floatBtn = fb;
        }
    }
    function removeLaunchers() {
        if (st.menuBtn) { try { st.menuBtn.remove(); } catch (_) { } st.menuBtn = null; }
        if (st.floatBtn) { try { st.floatBtn.remove(); } catch (_) { } st.floatBtn = null; }
        var orphan = document.getElementById(FLOAT_BTN_ID);
        if (orphan) { try { orphan.remove(); } catch (_) { } }
    }

    // ------------------------------------------------------------- image ops
    function specUrlOf(r) {
        return r && r.has_spec && r.spec_url ? (apiBase() + r.spec_url) : '';
    }
    function paintUrlOf(r) {
        return r && r.has_paint && r.paint_url ? (apiBase() + r.paint_url) : '';
    }

    function loadImage(url) {
        return new Promise(function (resolve, reject) {
            var img = new Image();
            // Same-origin in the packaged app; anonymous keeps the canvas
            // untainted in file://-dev (mirrors showSpecChannels,
            // paint-booth-5-api-render.js:3766).
            img.crossOrigin = 'anonymous';
            img.onload = function () { resolve(img); };
            img.onerror = function () { reject(new Error('image failed to load: ' + url)); };
            img.src = url;
        });
    }

    function imageDataOf(img, w, h) {
        var c = document.createElement('canvas');
        c.width = w; c.height = h;
        var ctx = c.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, w, h);
        return ctx.getImageData(0, 0, w, h);   // throws SecurityError if tainted
    }

    // Lazily-built, cached frames for the viewer.
    function frameCanvas(which, ch) {
        var key = which + ':' + ch;
        if (st.frameCache[key]) return st.frameCache[key];
        var src = which === 'a' ? st.aData : st.bData;
        if (!src) return null;
        var c = document.createElement('canvas');
        c.width = st.w; c.height = st.h;
        var ctx = c.getContext('2d');
        if (ch === 'all') {
            ctx.putImageData(src, 0, 0);
        } else {
            // Photoshop channels-in-color, identical math to the channel dock
            // (paint-booth-2-state-zones.js:3957-3963).
            var idx = CH_IDX[ch], t = TINTS[ch];
            var out = ctx.createImageData(st.w, st.h);
            var d = src.data, od = out.data;
            for (var i = 0; i < d.length; i += 4) {
                var v = d[i + idx];
                od[i] = Math.min(255, Math.round(v * t[0]));
                od[i + 1] = Math.min(255, Math.round(v * t[1]));
                od[i + 2] = Math.min(255, Math.round(v * t[2]));
                od[i + 3] = 255;
            }
            ctx.putImageData(out, 0, 0);
        }
        st.frameCache[key] = c;
        return c;
    }

    function deltaCanvas(ch) {
        var key = 'd:' + ch + ':' + st.gain;
        if (st.frameCache[key]) return st.frameCache[key];
        if (!st.aData || !st.bData) return null;
        var c = document.createElement('canvas');
        c.width = st.w; c.height = st.h;
        var ctx = c.getContext('2d');
        var out = ctx.createImageData(st.w, st.h);
        var a = st.aData.data, b = st.bData.data, od = out.data;
        var g = st.gain, t = ch === 'all' ? null : TINTS[ch], idx = ch === 'all' ? -1 : CH_IDX[ch];
        for (var i = 0; i < a.length; i += 4) {
            if (ch === 'all') {
                // Composite heat: R=|ΔM| G=|ΔR| B=|ΔCc| — each channel's motion
                // glows in its own Photoshop hue.
                var dm = a[i] - b[i]; if (dm < 0) dm = -dm;
                var dr = a[i + 1] - b[i + 1]; if (dr < 0) dr = -dr;
                var dc = a[i + 2] - b[i + 2]; if (dc < 0) dc = -dc;
                od[i] = Math.min(255, dm * g);
                od[i + 1] = Math.min(255, dr * g);
                od[i + 2] = Math.min(255, dc * g);
            } else {
                var dv = a[i + idx] - b[i + idx]; if (dv < 0) dv = -dv;
                dv = Math.min(255, dv * g);
                od[i] = Math.round(dv * t[0]);
                od[i + 1] = Math.round(dv * t[1]);
                od[i + 2] = Math.round(dv * t[2]);
            }
            od[i + 3] = 255;
        }
        ctx.putImageData(out, 0, 0);
        st.frameCache[key] = c;
        return c;
    }

    // ---------------------------------------------------------------- viewer
    function el(id) { return document.getElementById(id); }

    function blit(frame) {
        var cv = el('spbExpBlinkCanvas');
        if (!cv || !frame) return;
        if (cv.width !== st.w || cv.height !== st.h) { cv.width = st.w; cv.height = st.h; }
        var ctx = cv.getContext('2d');
        ctx.clearRect(0, 0, st.w, st.h);
        ctx.drawImage(frame, 0, 0);
    }

    function setBadge(text, cls) {
        var b = el('spbExpBlinkBadge');
        if (!b) return;
        b.textContent = text;
        b.className = 'spb-exp-blink-badge' + (cls ? ' ' + cls : '');
    }

    function stopBlink() {
        if (st.blinkTimer) { clearInterval(st.blinkTimer); st.blinkTimer = null; }
    }

    function renderView() {
        if (!st.aData || !st.bData) return;
        stopBlink();
        if (st.view === 'blink') {
            st.showA = true;
            var tick = function () {
                var frame = frameCanvas(st.showA ? 'a' : 'b', st.channel);
                blit(frame);
                setBadge(st.showA ? 'A — LATEST' : 'B — PREVIOUS', st.showA ? '' : 'is-b');
                st.showA = !st.showA;
            };
            tick();
            st.blinkTimer = setInterval(tick, st.blinkMs);
        } else {
            blit(deltaCanvas(st.channel));
            var chTxt = st.channel === 'all' ? 'M+R+Cc' : CH_NAME[st.channel];
            setBadge('|Δ| ' + chTxt + ' ×' + st.gain, 'is-delta');
        }
        syncChips();
    }

    function syncChips() {
        var ov = el(OVERLAY_ID);
        if (!ov) return;
        var chips = ov.querySelectorAll('.spb-exp-blink-chip');
        for (var i = 0; i < chips.length; i++) {
            var c = chips[i];
            var kind = c.getAttribute('data-kind');
            var val = c.getAttribute('data-val');
            var active =
                (kind === 'view' && val === st.view) ||
                (kind === 'ch' && val === st.channel) ||
                (kind === 'gain' && Number(val) === st.gain) ||
                (kind === 'speed' && Number(val) === st.blinkMs);
            c.classList.toggle('active', active);
        }
        // gain chips only matter in delta view; speed chips only in blink view
        var gainRow = el('spbExpBlinkGainRow');
        if (gainRow) gainRow.style.display = st.view === 'delta' ? '' : 'none';
        var speedRow = el('spbExpBlinkSpeedRow');
        if (speedRow) speedRow.style.display = st.view === 'blink' ? '' : 'none';
    }

    function onCanvasMove(e) {
        var cv = el('spbExpBlinkCanvas'), ro = el('spbExpBlinkReadout');
        if (!cv || !ro || !st.aData || !st.bData) return;
        var rect = cv.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        var x = Math.floor((e.clientX - rect.left) / rect.width * st.w);
        var y = Math.floor((e.clientY - rect.top) / rect.height * st.h);
        if (x < 0 || y < 0 || x >= st.w || y >= st.h) { ro.style.display = 'none'; return; }
        var i = (y * st.w + x) * 4;
        var a = st.aData.data, b = st.bData.data;
        var f = function (bi, ai) {
            var d = ai - bi;
            return bi + '→' + ai + (d ? ' (' + (d > 0 ? '+' : '') + d + ')' : '');
        };
        ro.textContent = '(' + x + ',' + y + ')  M ' + f(b[i], a[i]) +
            ' · R ' + f(b[i + 1], a[i + 1]) + ' · Cc ' + f(b[i + 2], a[i + 2]);
        ro.style.display = '';
    }
    function onCanvasLeave() {
        var ro = el('spbExpBlinkReadout');
        if (ro) ro.style.display = 'none';
    }

    // ------------------------------------------------------------ zone logic
    // Zone-layout signature: recipe.json's zoneSnapshot drops regionMask
    // (paint-booth-5-api-render.js:3739), so the only honest per-zone clip is
    // the CURRENT masks — valid only when the live layout matches BOTH recipes.
    function zoneSig(list) {
        if (!Array.isArray(list)) return null;
        var parts = [];
        for (var i = 0; i < list.length; i++) {
            var z = list[i] || {};
            parts.push((z.name || '') + ':' + (z.useRegion ? 1 : 0));
        }
        return parts.join('|');
    }

    function recipeSnap(idx) {
        var r = st.renders[idx];
        var snap = r && r.recipe && r.recipe.zoneSnapshot;
        return (Array.isArray(snap) && snap.length) ? snap : null;
    }

    // Count masked pixels whose spec moved ≥ MOVED_T on any channel. Mask
    // sampling matches the stats core: pixel centers, nearest neighbour
    // (paint-booth-specstats.js:139-142); A=0 on both frames = outside spec.
    function countMoved(mask, maskW, maskH) {
        var a = st.aData.data, b = st.bData.data, w = st.w, h = st.h;
        var sx = maskW / w, sy = maskH / h;
        var n = 0, moved = 0;
        for (var y = 0; y < h; y++) {
            var cy = y + 0.5;
            for (var x = 0; x < w; x++) {
                if (mask) {
                    var mx = ((x + 0.5) * sx) | 0; if (mx >= maskW) mx = maskW - 1;
                    var my = (cy * sy) | 0; if (my >= maskH) my = maskH - 1;
                    if (mask[my * maskW + mx] === 0) continue;
                }
                var i = (y * w + x) * 4;
                if (a[i + 3] === 0 && b[i + 3] === 0) continue;
                n++;
                var dm = a[i] - b[i]; if (dm < 0) dm = -dm;
                if (dm >= MOVED_T) { moved++; continue; }
                var dr = a[i + 1] - b[i + 1]; if (dr < 0) dr = -dr;
                if (dr >= MOVED_T) { moved++; continue; }
                var dc = a[i + 2] - b[i + 2]; if (dc < 0) dc = -dc;
                if (dc >= MOVED_T) moved++;
            }
        }
        return { n: n, moved: moved };
    }

    // Honest per-scope sentence: "Clearcoat 112 → 38 (satin clear → gloss
    // clear)" per channel whose MEDIAN moved ≥ MEDIAN_T, plus material verdict
    // change, plus % of pixels moved. B (older) → A (newer).
    function impactSentence(statsB, statsA, movedInfo) {
        var parts = [];
        var chans = [['m', 'metallic'], ['r', 'roughness'], ['c', 'clearcoat']];
        for (var i = 0; i < chans.length; i++) {
            var ch = chans[i][0], fld = chans[i][1];
            var sB = statsB && statsB[fld], sA = statsA && statsA[fld];
            if (!sB || !sA) continue;
            var d = sA.median - sB.median;
            if (Math.abs(d) >= MEDIAN_T) {
                var lb = chLabel(ch, sB.median), la = chLabel(ch, sA.median);
                var lblTxt = (lb && la) ? (lb === la ? ' (' + la + ')' : ' (' + lb + ' → ' + la + ')') : '';
                parts.push(CH_NAME[ch] + ' ' + sB.median + ' → ' + sA.median + lblTxt);
            }
        }
        if (statsB && statsA && statsB.material && statsA.material &&
            statsB.material.name !== statsA.material.name) {
            parts.push('material: ' + statsB.material.name + ' → ' + statsA.material.name);
        }
        var pct = movedInfo && movedInfo.n ? Math.round(100 * movedInfo.moved / movedInfo.n) : 0;
        var text = parts.length ? parts.join(' · ') : 'no median shift on any channel';
        if (!parts.length && pct < 1) text = 'no meaningful spec change';
        return { text: text, pct: pct };
    }

    function impactRowHTML(zoneName, sentence, finishId) {
        var swatch = '';
        if (finishId) {
            swatch = '<img class="spb-exp-blink-swatch" src="' + esc(finishSwatchUrl(finishId)) +
                '" title="' + esc(monolithicName(finishId)) + '" alt="" onerror="this.style.display=\'none\'">';
        }
        var quiet = sentence.pct < 1 ? ' is-quiet' : '';
        return '<div class="spb-exp-blink-impact-row">' + swatch +
            '<span class="spb-exp-blink-impact-zone" title="' + esc(zoneName) + '">' + esc(zoneName) + '</span>' +
            '<span class="spb-exp-blink-impact-text">' + esc(sentence.text) + '</span>' +
            '<span class="spb-exp-blink-impact-pct' + quiet + '">' + sentence.pct + '% moved</span>' +
            '</div>';
    }

    function buildImpact() {
        var box = el('spbExpBlinkImpact');
        if (!box || !st.aData || !st.bData) return;
        var seq = ++st.impactSeq;
        var core = statsCore();
        if (!core) {
            box.innerHTML = '<div class="spb-exp-blink-impact-head">Per-zone impact</div>' +
                '<div class="spb-exp-blink-impact-note">SPB_SpecStats core not loaded ' +
                '(paint-booth-specstats.js) — sentences unavailable, blink/heat views still work.</div>';
            return;
        }

        // Zone trust check (see header): live layout must match BOTH recipes.
        var zs = liveZones();
        var canvas = document.getElementById('paintCanvas');
        var cw = canvas ? canvas.width : 0, chh = canvas ? canvas.height : 0;
        var liveSig = zoneSig(zs);
        var sigA = zoneSig(recipeSnap(st.aIdx));
        var sigB = zoneSig(recipeSnap(st.bIdx));
        var zonesTrusted = !!(zs && zs.length && cw > 0 && chh > 0 &&
            sigA !== null && sigB !== null && liveSig === sigA && liveSig === sigB);

        var noteTxt;
        if (zonesTrusted) {
            noteTxt = 'Zone layout matches both recipes — clipping the delta to each ' +
                'current zone’s painted region mask. B (previous) → A (latest); medians.';
        } else if (!zs || !zs.length) {
            noteTxt = 'No live zones — whole-livery stats only.';
        } else if (sigA === null || sigB === null) {
            noteTxt = 'One of the two renders has no saved recipe (zoneSnapshot) — zone masks ' +
                'can’t be trusted across them, so whole-livery stats only.';
        } else {
            noteTxt = 'Zone layout CHANGED between these renders and now — the current masks ' +
                'don’t describe both frames, so whole-livery stats only (honest fallback).';
        }

        box.innerHTML = '<div class="spb-exp-blink-impact-head">Impact — what your tweak changed</div>' +
            '<div class="spb-exp-blink-impact-note">' + esc(noteTxt) + '</div>' +
            '<div class="spb-exp-blink-impact-note" id="spbExpBlinkImpactBusy">Analyzing…</div>';

        var w = st.w, h = st.h;
        var tasks = [];

        // Whole-livery row always leads.
        tasks.push(function () {
            var sA = null, sB = null;
            try { sA = core.computeZoneSpecStats(st.aData.data, w, h, {}); } catch (_) { }
            try { sB = core.computeZoneSpecStats(st.bData.data, w, h, {}); } catch (_) { }
            if (!sA || !sB) return '';
            return impactRowHTML('Whole livery', impactSentence(sB, sA, countMoved(null, w, h)), null);
        });

        var skippedNoMask = 0;
        if (zonesTrusted) {
            zs.forEach(function (z, zi) {
                // Same mask-validity test as the Spec Stats panel
                // (paint-booth-2-state-zones.js:4254): canvas-res Uint8 mask.
                if (!z || !z.regionMask || z.regionMask.length !== cw * chh ||
                    !z.regionMask.some || !z.regionMask.some(function (v) { return v > 0; })) {
                    skippedNoMask++;
                    return;
                }
                var mask = z.regionMask, name = z.name || ('Zone ' + (zi + 1));
                var finishId = z.finish || null;
                tasks.push(function () {
                    var opts = { mask: mask, maskW: cw, maskH: chh };
                    var sA = null, sB = null;
                    try { sA = core.computeZoneSpecStats(st.aData.data, w, h, opts); } catch (_) { }
                    try { sB = core.computeZoneSpecStats(st.bData.data, w, h, opts); } catch (_) { }
                    if (!sA || !sB) return '';
                    return impactRowHTML(name, impactSentence(sB, sA, countMoved(mask, cw, chh)), finishId);
                });
            });
        }

        // Run tasks one per tick so a 2048² spec times N zones can't lock the UI.
        var results = [];
        (function step(idx) {
            if (seq !== st.impactSeq) return;          // stale (new pair picked / closed)
            if (idx >= tasks.length) {
                var busy = el('spbExpBlinkImpactBusy');
                if (busy) {
                    if (skippedNoMask > 0) {
                        busy.textContent = skippedNoMask + ' zone(s) without a painted region mask are ' +
                            'covered by the whole-livery row.';
                    } else {
                        busy.remove();
                    }
                }
                return;
            }
            var html = '';
            try { html = tasks[idx]() || ''; } catch (e) {
                try { console.warn('[spec-blink-diff] impact row failed:', e); } catch (_) { }
            }
            if (seq !== st.impactSeq) return;
            if (html) {
                results.push(html);
                var busy2 = el('spbExpBlinkImpactBusy');
                if (busy2) busy2.insertAdjacentHTML('beforebegin', html);
            }
            setTimeout(function () { step(idx + 1); }, 0);
        })(0);
    }

    // -------------------------------------------------------------- revert
    function revertToB() {
        if (st.bIdx < 0 || !recipeSnap(st.bIdx)) {
            toast('No recipe saved for render B', true);
            return;
        }
        // Preferred: the stock full-fidelity restore path
        // (restoreRecipeFromRecent, paint-booth-5-api-render.js:5543 — confirm()
        // + _recipeSnapshotToZones + renderZones + triggerPreviewRender + autoSave).
        // It reads window._recentRendersCache (:5545), which the stock panel
        // also populates from the SAME /recent-renders/list payload (:5506).
        if (typeof window.restoreRecipeFromRecent === 'function') {
            window._recentRendersCache = st.renders;
            closePanel();
            window.restoreRecipeFromRecent(st.bIdx);
            return;
        }
        // Fallback: canonical zone installer (paint-booth-5-api-render.js:5435).
        if (typeof window.spbApplyZones === 'function') {
            if (!confirm('Restore render B’s full recipe? Your current zones will be replaced.')) return;
            closePanel();
            window.spbApplyZones(recipeSnap(st.bIdx));
            return;
        }
        toast('Restore path unavailable (restoreRecipeFromRecent / spbApplyZones missing)', true);
    }

    // ---------------------------------------------------------------- panel
    function setStatus(msg, isErr) {
        var s = el('spbExpBlinkStatus');
        if (!s) return;
        s.textContent = msg || '';
        s.classList.toggle('is-error', !!isErr);
    }

    function pickable(renders) {
        var out = [];
        for (var i = 0; i < renders.length; i++) {
            if (renders[i] && renders[i].has_spec) out.push(i);
        }
        return out;
    }

    function renderStrip() {
        var strip = el('spbExpBlinkStrip');
        if (!strip) return;
        var html = st.renders.map(function (r, i) {
            var rec = r.recipe || {};
            var when = rec.timestamp ? new Date(rec.timestamp).toLocaleString() : (r.slot || '');
            var thumb = specUrlOf(r) || paintUrlOf(r);
            var cls = 'spb-exp-blink-pick' + (i === st.aIdx ? ' is-a' : '') + (i === st.bIdx ? ' is-b' : '');
            var tag = i === st.aIdx ? 'A' : (i === st.bIdx ? 'B' : '');
            var dis = r.has_spec ? '' : ' disabled title="no spec.png saved for this render"';
            return '<div class="' + cls + '" data-idx="' + i + '">' +
                (tag ? '<span class="spb-exp-blink-abtag">' + tag + '</span>' : '') +
                (thumb ? '<img src="' + esc(thumb) + '" alt="spec thumbnail">'
                    : '<div style="aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;color:var(--text-dim,#6b7787);">no image</div>') +
                '<div class="spb-exp-blink-when">' + esc(when) + '</div>' +
                '<div class="spb-exp-blink-summary" title="' + esc(rec.zones_summary || '') + '">' +
                esc(rec.zones_summary || '—') + '</div>' +
                '<div class="spb-exp-blink-pickbtns">' +
                '<button type="button" data-pick="a" data-idx="' + i + '"' + dis +
                (i === st.aIdx ? ' class="active-a"' : '') + '>A</button>' +
                '<button type="button" data-pick="b" data-idx="' + i + '"' + dis +
                (i === st.bIdx ? ' class="active-b"' : '') + '>B</button>' +
                '</div></div>';
        }).join('');
        strip.innerHTML = html ||
            '<div class="spb-exp-blink-impact-note">No saved renders yet — render a car twice ' +
            '(the app auto-saves the last 10: paint.png + spec.png + recipe.json).</div>';
        var rv = el('spbExpBlinkRevert');
        if (rv) rv.disabled = !(st.bIdx >= 0 && recipeSnap(st.bIdx));
    }

    function onStripClick(e) {
        var btn = e.target && e.target.closest ? e.target.closest('button[data-pick]') : null;
        if (!btn || btn.disabled) return;
        var idx = Number(btn.getAttribute('data-idx'));
        var which = btn.getAttribute('data-pick');
        if (!(idx >= 0) || idx >= st.renders.length) return;
        if (which === 'a') {
            st.aIdx = idx;
            if (st.bIdx === idx) st.bIdx = -1;
        } else {
            st.bIdx = idx;
            if (st.aIdx === idx) st.aIdx = -1;
        }
        renderStrip();
        loadPair();
    }

    function loadPair() {
        if (st.aIdx < 0 || st.bIdx < 0 || st.aIdx === st.bIdx) {
            setStatus('Pick two different renders (A = after, B = before).');
            return;
        }
        var ra = st.renders[st.aIdx], rb = st.renders[st.bIdx];
        var ua = specUrlOf(ra), ub = specUrlOf(rb);
        if (!ua || !ub) {
            setStatus('Both picks need a saved spec.png — choose renders with a spec thumbnail.', true);
            return;
        }
        var mySeq = ++st.impactSeq;   // cancel any in-flight impact build
        stopBlink();
        st.aData = null; st.bData = null; st.frameCache = {}; st.resampled = false;
        setStatus('Loading spec maps…');
        Promise.all([loadImage(ua), loadImage(ub)]).then(function (imgs) {
            if (!st.open || mySeq !== st.impactSeq) return;
            var ia = imgs[0], ib = imgs[1];
            st.w = ia.naturalWidth; st.h = ia.naturalHeight;
            st.resampled = (ib.naturalWidth !== st.w || ib.naturalHeight !== st.h);
            try {
                st.aData = imageDataOf(ia, st.w, st.h);
                st.bData = imageDataOf(ib, st.w, st.h);   // B resampled into A's grid if needed
            } catch (err) {
                setStatus('Cannot read spec pixels (canvas tainted — cross-origin dev page?): ' + err, true);
                return;
            }
            var whole = countMoved(null, st.w, st.h);
            var pct = whole.n ? Math.round(100 * whole.moved / whole.n) : 0;
            setStatus('A ' + st.w + '×' + st.h +
                (st.resampled ? ' · B was a different size — resampled to match (values approximate)' : '') +
                ' · ' + pct + '% of spec pixels moved ≥' + MOVED_T + ' levels.',
                false);
            renderView();
            buildImpact();
        }).catch(function (err) {
            if (!st.open) return;
            setStatus('Could not load the two spec.pngs: ' + (err && err.message || err), true);
        });
    }

    function openPanel() {
        if (!st.enabled) return;
        if (st.open) { closePanel(); }
        st.open = true;

        var ov = document.createElement('div');
        ov.id = OVERLAY_ID;
        ov.className = 'spb-exp-blink-overlay';
        ov.innerHTML =
            '<div class="spb-exp-blink-card" role="dialog" aria-label="Spec Blink Diff">' +
            '<div class="spb-exp-blink-header">' +
            '<h3>🔭 SPEC BLINK DIFF — experimental</h3>' +
            '<span class="spb-exp-blink-spacer"></span>' +
            '<button type="button" class="btn btn-sm spb-exp-blink-revert" id="spbExpBlinkRevert" disabled ' +
            'title="Restore render B’s full recipe (same path as the recall panel’s Load recipe)">↺ Revert to B</button>' +
            '<button type="button" class="btn btn-sm" id="spbExpBlinkClose" aria-label="Close blink diff">&times; Close</button>' +
            '</div>' +
            '<div class="spb-exp-blink-body">' +
            '<div class="spb-exp-blink-strip" id="spbExpBlinkStrip"></div>' +
            '<div class="spb-exp-blink-chips">' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="view" data-val="blink">Blink A/B</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="view" data-val="delta">|Δ| Heat</button>' +
            '<span class="spb-exp-blink-chiplabel">channel</span>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="ch" data-val="all">All</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="ch" data-ch="m" data-val="m">M — Metallic</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="ch" data-ch="r" data-val="r">R — Roughness</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="ch" data-ch="c" data-val="c">Cc — Clearcoat</button>' +
            '<span id="spbExpBlinkSpeedRow">' +
            '<span class="spb-exp-blink-chiplabel">speed</span>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="speed" data-val="1000">1 Hz</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="speed" data-val="500">2 Hz</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="speed" data-val="250">4 Hz</button>' +
            '</span>' +
            '<span id="spbExpBlinkGainRow" style="display:none;">' +
            '<span class="spb-exp-blink-chiplabel">gain</span>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="gain" data-val="1">×1</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="gain" data-val="4">×4</button>' +
            '<button type="button" class="spb-exp-blink-chip" data-kind="gain" data-val="8">×8</button>' +
            '</span>' +
            '</div>' +
            '<div class="spb-exp-blink-viewwrap">' +
            '<canvas class="spb-exp-blink-canvas" id="spbExpBlinkCanvas" width="4" height="4"></canvas>' +
            '<div class="spb-exp-blink-badge" id="spbExpBlinkBadge">pick A and B above</div>' +
            '<div class="spb-exp-blink-readout" id="spbExpBlinkReadout"></div>' +
            '</div>' +
            '<div class="spb-exp-blink-status" id="spbExpBlinkStatus">Loading recent renders…</div>' +
            '<div class="spb-exp-blink-impact" id="spbExpBlinkImpact"></div>' +
            '</div></div>';

        document.body.appendChild(ov);

        // Overlay-local listeners die with the overlay node on closePanel();
        // only the document-level Escape handler needs explicit removal.
        ov.addEventListener('click', function (e) { if (e.target === ov) closePanel(); });
        el('spbExpBlinkClose').addEventListener('click', closePanel);
        el('spbExpBlinkRevert').addEventListener('click', revertToB);
        el('spbExpBlinkStrip').addEventListener('click', onStripClick);
        el('spbExpBlinkCanvas').addEventListener('mousemove', onCanvasMove);
        el('spbExpBlinkCanvas').addEventListener('mouseleave', onCanvasLeave);
        ov.addEventListener('click', function (e) {
            var chip = e.target && e.target.closest ? e.target.closest('.spb-exp-blink-chip') : null;
            if (!chip) return;
            var kind = chip.getAttribute('data-kind'), val = chip.getAttribute('data-val');
            if (kind === 'view') st.view = val;
            else if (kind === 'ch') { st.channel = val; }
            else if (kind === 'gain') { st.gain = Number(val) || 4; }
            else if (kind === 'speed') { st.blinkMs = Number(val) || BLINK_MS_DEFAULT; }
            renderView();
        });
        st._escHandler = function (e) {
            if (e.key === 'Escape' && st.open) { e.stopPropagation(); closePanel(); }
        };
        document.addEventListener('keydown', st._escHandler, true);

        syncChips();

        // Fetch the rotating last-10 (server_routes/render_file_routes.py:295).
        fetch(apiBase() + '/recent-renders/list', { signal: AbortSignal.timeout(15000) })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!st.open) return;
                st.renders = (data && data.renders) || [];
                var picks = pickable(st.renders);
                st.aIdx = picks.length > 0 ? picks[0] : -1;   // latest
                st.bIdx = picks.length > 1 ? picks[1] : -1;   // previous
                renderStrip();
                if (picks.length < 2) {
                    setStatus('Need at least 2 saved renders with a spec map. Render, tweak a slider, ' +
                        'render again — then reopen this tool.', true);
                } else {
                    loadPair();
                }
            })
            .catch(function (err) {
                if (!st.open) return;
                setStatus('Could not load recent renders: ' + (err && err.message || err), true);
                renderStrip();
            });
    }

    function closePanel() {
        st.open = false;
        st.impactSeq++;               // cancel async impact build
        stopBlink();
        if (st._escHandler) {
            try { document.removeEventListener('keydown', st._escHandler, true); } catch (_) { }
            st._escHandler = null;
        }
        var ov = el(OVERLAY_ID);
        if (ov) ov.remove();
        // Free the big pixel buffers; the recall list itself is tiny.
        st.aData = null; st.bData = null; st.frameCache = {};
    }

    // ------------------------------------------------------ enable / disable
    function enable() {
        if (st.enabled) return;
        st.enabled = true;
        injectStyle();
        addLaunchers();
    }

    function disable() {
        if (!st.enabled) return;
        st.enabled = false;
        closePanel();
        removeLaunchers();
        offAll();
        removeStyle();
        st.renders = [];
        st.aIdx = -1; st.bIdx = -1;
    }

    // ------------------------------------------------------------- register
    window.SPB_EXPERIMENTS = window.SPB_EXPERIMENTS || [];
    window.SPB_EXPERIMENTS.push({
        id: EXP_ID,
        name: EXP_NAME,
        pitch: EXP_PITCH,
        enable: enable,
        disable: disable
    });
})();
