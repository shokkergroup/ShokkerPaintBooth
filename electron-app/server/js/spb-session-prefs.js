/* ============================================================================
 * SPB SESSION PREFS — the settings a painter should never have to re-enter
 *                                                        2026-08-05, Claude
 *
 * TWO VERIFIED GAPS (audited in the live DOM + getConfig, not guessed):
 *
 * 1. TOOL SETTINGS RESET EVERY SESSION. Nine controls — brush size / hardness /
 *    opacity, wand tolerance / sample size / contiguous / anti-alias, selection
 *    feather, selection mode — are read at use time from the DOM but are in
 *    neither getConfig() nor localStorage. A painter who always works at
 *    tolerance 45 with a 12px feather re-enters both at every launch.
 *
 * 2. NO RECENT PAINT FILES. Only THE last paint is remembered (for boot
 *    restore). A painter switching between cars re-navigates the folder tree
 *    every time. The custom file picker's quick-nav shows drives and server
 *    shortcuts, but nothing about the painter's own history.
 *
 * DESIGN CONSTRAINTS
 *  - Zero coupling to app closures: everything here works through DOM ids,
 *    events, and window.* functions that already exist. If any of them are
 *    missing, the module quietly does nothing (never breaks the app).
 *  - Restore must not fight boot: values are applied only once the controls
 *    exist, and each restored control gets input+change events so its live
 *    label / internal mirror syncs the same way a human edit would.
 *  - The recents section must not repeat the pack-03 mistake: it re-renders on
 *    quick-nav rebuilds via a MutationObserver that DISCONNECTS while it
 *    mutates, and only writes when its section is actually absent.
 * ==========================================================================*/
(function () {
    'use strict';

    var PREFS_KEY = 'spb_tool_prefs_v1';
    var RECENTS_KEY = 'spb_recent_paints_v1';
    var RECENTS_MAX = 8;

    /* ------------------------------------------------------------------ *
     * 1. TOOL SETTING PERSISTENCE
     * ------------------------------------------------------------------ */
    var TOOL_IDS = [
        'brushSize', 'brushHardness', 'brushOpacity',
        'wandTolerance', 'wandSampleSize', 'wandContiguous', 'wandAntiAlias',
        'selectionFeather', 'selectionMode'
    ];

    function readControl(el) {
        if (el.type === 'checkbox') return { c: !!el.checked };
        return { v: el.value };
    }

    function writeControl(el, saved) {
        if (el.type === 'checkbox') {
            if (typeof saved.c !== 'boolean' || el.checked === saved.c) return false;
            el.checked = saved.c;
        } else {
            if (saved.v == null || String(el.value) === String(saved.v)) return false;
            el.value = saved.v;
        }
        // Fire the same events a human edit fires so live labels and any
        // mirrored internal state update through their normal handlers.
        try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (_) {}
        try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch (_) {}
        return true;
    }

    var _saveTimer = null;
    function savePrefsSoon() {
        if (_saveTimer) clearTimeout(_saveTimer);
        _saveTimer = setTimeout(function () {
            _saveTimer = null;
            var out = {};
            TOOL_IDS.forEach(function (id) {
                var el = document.getElementById(id);
                if (el) out[id] = readControl(el);
            });
            try { localStorage.setItem(PREFS_KEY, JSON.stringify(out)); } catch (_) {}
        }, 300);
    }

    function restorePrefs() {
        var saved = null;
        try { saved = JSON.parse(localStorage.getItem(PREFS_KEY) || 'null'); } catch (_) {}
        if (!saved) return 0;
        var restored = 0;
        TOOL_IDS.forEach(function (id) {
            var el = document.getElementById(id);
            if (el && saved[id] && writeControl(el, saved[id])) restored++;
        });
        return restored;
    }

    function armPrefs() {
        // one delegated listener catches all nine controls wherever the active
        // experience pack has moved them (moves preserve ids)
        document.addEventListener('input', function (e) {
            if (e.target && TOOL_IDS.indexOf(e.target.id) >= 0) savePrefsSoon();
        }, true);
        document.addEventListener('change', function (e) {
            if (e.target && TOOL_IDS.indexOf(e.target.id) >= 0) savePrefsSoon();
        }, true);
    }

    /* ------------------------------------------------------------------ *
     * 2. RECENT PAINT FILES
     * ------------------------------------------------------------------ */
    function getRecents() {
        try {
            var r = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
            return Array.isArray(r) ? r : [];
        } catch (_) { return []; }
    }

    function notePaint(path) {
        var p = String(path || '').trim();
        if (!p) return;
        // Only real paint sources belong here — not spec maps someone previewed.
        if (!/\.(tga|psd|png|jpg|jpeg|bmp)$/i.test(p)) return;
        var r = getRecents().filter(function (e) { return e && e.path !== p; });
        r.unshift({ path: p, t: Date.now() });
        if (r.length > RECENTS_MAX) r.length = RECENTS_MAX;
        try { localStorage.setItem(RECENTS_KEY, JSON.stringify(r)); } catch (_) {}
    }

    function hookLoadPaint() {
        var orig = window.loadPaintByPath;
        if (typeof orig !== 'function' || orig._spbRecentsWrapped) return false;
        var wrapped = function (path) {
            var ok = orig.apply(this, arguments);
            // record only when the app actually accepted the load
            if (ok !== false) notePaint(path);
            return ok;
        };
        wrapped._spbRecentsWrapped = true;
        window.loadPaintByPath = wrapped;
        return true;
    }

    function baseName(p) {
        var parts = String(p).split(/[\\\/]/);
        return parts[parts.length - 1] || p;
    }

    function renderRecents(quickNav) {
        if (!quickNav || document.getElementById('spbRecentPaints')) return;
        var overlay = document.getElementById('filePickerOverlay');
        // Folder picks (output dir etc.) must not offer paint FILES.
        if (overlay && overlay.dataset.fpMode === 'folder') return;
        var recents = getRecents();
        if (!recents.length) return;

        var wrap = document.createElement('div');
        wrap.id = 'spbRecentPaints';
        wrap.style.cssText = 'display:flex; flex-wrap:wrap; gap:4px; width:100%;' +
                             'padding:2px 0 6px 0; border-bottom:1px solid rgba(255,255,255,0.08);' +
                             'margin-bottom:4px;';
        var tag = document.createElement('span');
        tag.textContent = 'RECENT';
        tag.style.cssText = 'font-size:9px; letter-spacing:1px; opacity:0.55;' +
                            'align-self:center; padding:0 4px;';
        wrap.appendChild(tag);

        recents.forEach(function (e) {
            var b = document.createElement('button');
            b.type = 'button';
            b.textContent = '⏱ ' + baseName(e.path);
            b.title = e.path;
            b.addEventListener('click', function (ev) {
                ev.stopPropagation();
                // Route through the picker's OWN select flow (visible path field +
                // Select button) so whatever callback this picker was opened with
                // receives the path — works for paint loads, spec maps, anything.
                var input = document.getElementById('filePickerPath');
                var btn = document.getElementById('filePickerSelectBtn');
                if (input && btn) {
                    input.value = e.path;
                    btn.disabled = false;
                    btn.click();
                }
            });
            wrap.appendChild(b);
        });
        quickNav.insertBefore(wrap, quickNav.firstChild);
    }

    function armRecentsInPicker() {
        var quickNav = document.getElementById('filePickerQuickNav');
        if (!quickNav) return false;
        // The picker rebuilds quick-nav innerHTML on every navigate, wiping our
        // section. Re-add it — with the observer DISCONNECTED while we mutate
        // (the xp-03 lesson: an observer that writes into its own subtree with
        // subtree:true is an infinite microtask loop that kills the renderer).
        var mo = new MutationObserver(function () {
            if (document.getElementById('spbRecentPaints')) return;
            mo.disconnect();
            try { renderRecents(quickNav); }
            finally { mo.observe(quickNav, { childList: true }); }
        });
        mo.observe(quickNav, { childList: true });
        return true;
    }

    /* ------------------------------------------------------------------ *
     * boot: wait until the app's controls exist, then arm everything once
     * ------------------------------------------------------------------ */
    var _tries = 0;
    function boot() {
        _tries++;
        var ready = document.getElementById('wandTolerance') &&
                    typeof window.loadPaintByPath === 'function';
        if (!ready && _tries < 240) { setTimeout(boot, 250); return; }   // ~60s ceiling
        try { armPrefs(); } catch (_) {}
        try { hookLoadPaint(); } catch (_) {}
        try { armRecentsInPicker(); } catch (_) {}
        try {
            var n = restorePrefs();
            if (n > 0 && typeof window.showToast === 'function') {
                window.showToast('Restored your tool settings (' + n + ')', 'info');
            }
        } catch (_) {}
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

    window.SPBSessionPrefs = { notePaint: notePaint, getRecents: getRecents,
                               restorePrefs: restorePrefs, PREFS_KEY: PREFS_KEY,
                               RECENTS_KEY: RECENTS_KEY };
})();
