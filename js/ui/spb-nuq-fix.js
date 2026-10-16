/* [SPB-NUQ-FIX 2026-10-10] fixes from the first-hour new-user QA (_easy_claude_work/newuser_qa/PROGRESS.md "REPORT").
   Small, additive, each with its own guard. KILL SWITCH for every item: window.SPB_NUQ_OFF = true  (or localStorage SPB_NUQ_OFF = "1").
   #3  Spec Sculpt button opens the Spec Sculpt lab itself (its own window; Esc / back arrow there return to this editor).
   #7  Helper dock folds when the chat view is left and opens where it hides nothing.   #8  "+ Layer" = blank layer; Actions > Place image...
*/
(function () {
    'use strict';
    if (window.SpbNuq) return;
    var doc = document;

    function off() {
        try { if (window.SPB_NUQ_OFF) return true; } catch (_) {}
        try { return localStorage.getItem('SPB_NUQ_OFF') === '1'; } catch (_) { return false; }
    }

    var api = { off: off };

    /* ---- #3 Spec Sculpt routing ------------------------------------------------------------------------------------------------ */
    api.openSpecSculpt = function () {
        if (off()) { try { if (window.spbEasy && window.spbEasy.openSculpt) window.spbEasy.openSculpt(); } catch (_) {} return; }
        if (typeof window.openSpecSculptLab === 'function') window.openSpecSculptLab();
        else window.location.href = '/spec-sculpt.html';
    };

    /* ---- #7 Offline Helper dock must not hide the work ---------------------------------------------------------------------------
       a) leaving the chat view used to leave the helper OPEN as a 392x910 floating panel on top of the layers panel and the Live Preview;
          now it folds back to its small "AI" pill (one click opens it again).
       b) when the helper is opened inside the editor and the buyer has not dragged it yet, it goes where it hides nothing: the empty
          band under the Source / Live Preview panes if there is one, else a right-hand drawer that starts BELOW the toolbar rows.
          It is an overlay (position:fixed), so nothing else moves when it opens. A position the buyer dragged/saved is never touched. */
    function rect(sel) {
        var e = doc.querySelector(sel); if (!e) return null;
        var cs = window.getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null;
        var r = e.getBoundingClientRect(); return (r.width > 0 && r.height > 0) ? r : null;
    }
    /* the dock's own ResizeObserver saves its box 400 ms after ANY size change, including when it is hidden (0x0), and the next launch then
       restored a 320x240 box at (0,0) on top of the toolbar. A stored box that is too small to be a real one is dropped at load. */
    var UKEY = 'spb_nuq_dock_user';
    function sanitizeGeom() {
        if (off()) return;
        try { var g = JSON.parse(localStorage.getItem('spb_pro_ai_geom') || 'null'); if (g && (!(g.w >= 200) || !(g.h >= 100))) localStorage.removeItem('spb_pro_ai_geom'); } catch (_) {}
    }
    sanitizeGeom();
    function savedGeom() { try { return localStorage.getItem(UKEY) === '1'; } catch (_) { return false; } }   // true only after the buyer dragged / resized it
    function inEditor() { var b = doc.body; return !!b && !b.classList.contains('spb-chat-studio') && !b.classList.contains('spb-easy-on'); }
    function placeDock(d) {
        if (off() || !d || d.hidden || !inEditor() || savedGeom()) return;
        var vw = window.innerWidth, vh = window.innerHeight, topSafe = 0, i, r;
        ['header', '#spbTopToolbar', '.header'].forEach(function (s) { r = rect(s); if (r && r.bottom < vh * 0.45) topSafe = Math.max(topSafe, r.bottom); });
        var paneBottom = 0;
        ['#splitSource', '#splitPreview'].forEach(function (s) { r = rect(s); if (r) paneBottom = Math.max(paneBottom, r.bottom); });
        var vp = rect('#canvasViewport'), cmd = rect('.workbench-command-bar');
        var L, T, W, H;
        if (vp && paneBottom) {
            var bandL = vp.left + 8, bandR = vp.right - 8, bandT = paneBottom + 8, bandB = Math.min(vp.bottom, cmd ? cmd.top : vp.bottom) - 8;
            if (bandB - bandT >= 360 && bandR - bandL >= 360) { W = Math.min(bandR - bandL, 640); H = bandB - bandT; L = bandR - W; T = bandT; }
        }
        if (W == null) {   // no free band: a right-hand drawer under the toolbar rows (covers panels only because the buyer asked for it)
            W = Math.min(392, vw - 28); T = Math.max(topSafe + 8, 8); H = Math.max(240, vh - T - 12); L = vw - W - 14;
        }
        d.style.setProperty('left', Math.round(L) + 'px'); d.style.setProperty('top', Math.round(T) + 'px');
        d.style.setProperty('width', Math.round(W) + 'px'); d.style.setProperty('height', Math.round(H) + 'px');
        d.style.setProperty('min-height', '120px'); d.style.setProperty('right', 'auto'); d.style.setProperty('bottom', 'auto');
        d.setAttribute('data-nuq-placed', '1');
    }
    function foldDock() {
        if (off()) return;
        var d = doc.getElementById('spbProAI'); if (!d || d.hidden) return;
        var b = d.querySelector('[data-act="close"]'); if (b) b.click();
    }
    function watchDock() {
        var d = doc.getElementById('spbProAI');
        if (!d) { setTimeout(watchDock, 800); return; }
        var wasHidden = d.hidden;
        d.addEventListener('mousedown', function (e) {
            if (off() || !inEditor()) return;
            var r = d.getBoundingClientRect(), t = e.target, head = t && t.closest ? t.closest('.spb-pai-head') : null;
            if ((head && !(t.closest && t.closest('button'))) || (e.clientX > r.right - 22 && e.clientY > r.bottom - 22)) { try { localStorage.setItem(UKEY, '1'); } catch (_) {} }
        }, true);
        try {
            new MutationObserver(function () {
                if (wasHidden && !d.hidden) placeDock(d);
                if (d.hidden) d.removeAttribute('data-nuq-placed');
                wasHidden = d.hidden;
            }).observe(d, { attributes: true, attributeFilter: ['hidden'] });
        } catch (_) {}
        if (!d.hidden) placeDock(d);
    }
    window.addEventListener('spb:chat-studio', function (ev) {
        if (ev && ev.detail && ev.detail.open === false) setTimeout(foldDock, 0);
    });
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { setTimeout(watchDock, 1200); }); else setTimeout(watchDock, 1200);
    api.placeDock = function () { placeDock(doc.getElementById('spbProAI')); };

    /* ---- #8 "+ Layer" adds a BLANK layer (like every layer-based editor); a picture goes in through Actions > Place image... ---------- */
    api.addLayer = function () {
        if (off() || typeof window.addBlankLayer !== 'function') { if (typeof window.addLayerFromFile === 'function') window.addLayerFromFile(); return; }
        var l = window.addBlankLayer();
        try { if (typeof window.setToolbarEditMode === 'function') window.setToolbarEditMode('layer'); } catch (_) {}
        return l;
    };

    /* ---- shared helpers: one small stylesheet, a toast shortcut, a confirm dialog ---------------------------------------------------- */
    /* [LEFTOVERS-3 2026-10-10, item 5] lane kill switch: window.SPB_LO3_OFF / SPB_LO3_5_OFF (or the same name = '1' in localStorage) brings the old #13 rules back */
    function lo3Legacy13() {
        try { if (window.SPB_LO3_OFF || window.SPB_LO3_5_OFF) return true; } catch (_) {}
        try { return localStorage.getItem('SPB_LO3_OFF') === '1' || localStorage.getItem('SPB_LO3_5_OFF') === '1'; } catch (_) { return false; }
    }
    var styled = false;
    function ensureStyle() {
        if (styled || doc.getElementById('spbNuqStyle')) { styled = true; return; }
        styled = true;
        var st = doc.createElement('style'); st.id = 'spbNuqStyle';
        st.textContent = [
            '.spb-nuq-dlg-wrap{position:fixed;inset:0;z-index:100200;display:flex;align-items:center;justify-content:center;background:rgba(3,4,10,.62)}',
            '.spb-nuq-dlg{width:min(440px,92vw);box-sizing:border-box;background:var(--bg-card,#0e0e22);color:var(--text,#e8e8f0);border:1px solid var(--border,#2a2a4a);border-radius:12px;padding:16px 18px;box-shadow:0 18px 50px rgba(0,0,0,.55);font:13px/1.45 system-ui,sans-serif}',
            '.spb-nuq-dlg h3{margin:0 0 10px;font-size:15px;color:var(--text-bright,#f4f4ff)}',
            '.spb-nuq-row{display:flex;gap:12px;align-items:flex-start}',
            '.spb-nuq-thumb{width:84px;height:84px;border-radius:8px;border:1px solid var(--border,#2a2a4a);flex:none;object-fit:cover;background:#10241c}',
            '.spb-nuq-txt p{margin:0 0 6px}',
            '.spb-nuq-warn{margin:12px 0 0;padding:8px 10px;border-radius:8px;background:rgba(255,170,60,.12);border:1px solid rgba(255,170,60,.5)}',
            '.spb-nuq-btns{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}',
            '.spb-nuq-btns button{padding:6px 14px;border-radius:6px;border:1px solid var(--border,#2a2a4a);background:transparent;color:var(--text,#e8e8f0);font:inherit;font-weight:600;cursor:pointer}',
            '.spb-nuq-btns button.primary{border-color:var(--accent-cyan,#00e5ff);color:var(--accent-cyan,#00e5ff);background:rgba(0,229,255,.1)}',
            '.spb-nuq-btns button:focus-visible{outline:2px solid var(--accent-cyan,#00e5ff);outline-offset:2px}',
            '.spb-nuq-busy{cursor:progress!important;opacity:.8}',
            /* #14 notices never swallow clicks meant for the controls under them (only their own buttons take clicks) */
            '#toast{pointer-events:none!important}',
            '#toast [title="Dismiss"],#toast button{pointer-events:auto}',
            '#spbStaleBanner{z-index:1000!important;pointer-events:none}',
            '#spbStaleBanner button{pointer-events:auto}',
            '#spbServerBanner{pointer-events:none}',
            /* the header (z 5200) sat above the file picker (z 1100), so its title hid under the logo */
            'body #filePickerOverlay{z-index:5300!important}'
        ].concat(lo3Legacy13() ? [
            /* #13 render result: the buyer's own car first, the branded card smaller and below it.
               [LEFTOVERS-3 2026-10-10, item 5] NOT injected any more by default: the RENDER-CARD screen (js/ui/spb-render-card-20261010.js) now shows the buyer's
               PAINT + SPEC once, big, above the fold, so these rules only made the OLD modal (SPB_RENDER_CARD_OFF) show PAINT/SPEC twice and cap the card at 620 px.
               Kept verbatim behind the lane switch (SPB_LO3_OFF / SPB_LO3_5_OFF) so the 10-10 NUQ look can be brought back. */
            'body #renderResultsPanel.spb-render-modal>*{order:3}',
            'body #renderResultsPanel.spb-render-modal>div:first-of-type,body #renderResultsPanel.spb-render-modal>#renderStatusBanner{order:0}',
            'body #renderResultsPanel.spb-render-modal #renderCarPreviews{display:flex!important;order:1;flex:0 0 auto;gap:12px;max-height:none!important;overflow:hidden!important;padding:8px 4px 4px;justify-content:center;gap:28px}',
            'body #renderResultsPanel.spb-render-modal #renderCarPreviews>div{flex:0 1 auto!important;min-width:0}',
            'body #renderResultsPanel.spb-render-modal #renderCarPreviews img{max-height:32vh!important;max-width:100%;object-fit:contain}',
            'body #renderResultsPanel.spb-render-modal #renderCarPreviews img:not([src]),body #renderResultsPanel.spb-render-modal #renderCarPreviews img[src=""]{display:none}',
            'body #renderResultsPanel.spb-render-modal #recipeCardStage{order:2}',
            'body #renderResultsPanel.spb-render-modal .recipe-card-canvas{max-width:620px}'
        ] : []).join('\n');
        (doc.head || doc.documentElement).appendChild(st);
    }
    function toast(msg, kind) { try { if (typeof window.showToast === 'function') window.showToast(msg, kind || false); } catch (_) {} }
    var dlgOpen = false;
    /* confirmDialog({title, lines:[text], thumb, warn, okLabel, cancelLabel, focusCancel}) -> Promise<boolean>; Esc / click outside = cancel */
    function confirmDialog(o) {
        ensureStyle();
        return new Promise(function (resolve) {
            if (dlgOpen) { resolve(false); return; }
            dlgOpen = true;
            var prev = doc.activeElement;
            var wrap = doc.createElement('div'); wrap.className = 'spb-nuq-dlg-wrap';
            var box = doc.createElement('div'); box.className = 'spb-nuq-dlg'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', o.title);
            var h = doc.createElement('h3'); h.textContent = o.title; box.appendChild(h);
            var row = doc.createElement('div'); row.className = 'spb-nuq-row';
            if (o.thumb) { var im = doc.createElement('img'); im.className = 'spb-nuq-thumb'; im.alt = ''; im.src = o.thumb; im.onerror = function () { im.remove(); }; row.appendChild(im); }
            var tx = doc.createElement('div'); tx.className = 'spb-nuq-txt';
            (o.lines || []).forEach(function (t) { var p = doc.createElement('p'); p.textContent = t; tx.appendChild(p); });
            row.appendChild(tx); box.appendChild(row);
            if (o.warn) { var w = doc.createElement('div'); w.className = 'spb-nuq-warn'; w.setAttribute('role', 'alert'); w.textContent = o.warn; box.appendChild(w); }
            var bt = doc.createElement('div'); bt.className = 'spb-nuq-btns';
            var no = doc.createElement('button'); no.type = 'button'; no.textContent = o.cancelLabel || 'Cancel';
            var ok = doc.createElement('button'); ok.type = 'button'; ok.className = 'primary'; ok.textContent = o.okLabel || 'OK';
            bt.appendChild(no); bt.appendChild(ok); box.appendChild(bt); wrap.appendChild(box);
            function done(v) {
                if (!dlgOpen) return; dlgOpen = false;
                doc.removeEventListener('keydown', onKey, true);
                wrap.remove();
                try { if (prev && prev.focus) prev.focus(); } catch (_) {}
                resolve(!!v);
            }
            function onKey(e) {
                if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(false); }
                else if (e.key === 'Tab') { e.preventDefault(); (doc.activeElement === no ? ok : no).focus(); }
            }
            no.onclick = function () { done(false); }; ok.onclick = function () { done(true); };
            wrap.addEventListener('mousedown', function (e) { if (e.target === wrap) done(false); });
            doc.addEventListener('keydown', onKey, true);
            doc.body.appendChild(wrap);
            (o.focusCancel ? no : ok).focus();
        });
    }
    api.confirmDialog = confirmDialog;

    /* ---- #11 FRACTURE THIS PAINT shows what it will do and asks first; it never changes an empty zone silently ----------------------- */
    function zoneCovers(z) {
        if (!z) return false;
        try { if (z.regionMask && (typeof window._maskAny === 'function' ? window._maskAny(z.regionMask) : true)) return true; } catch (_) {}
        if (z.colorMode === 'multi') return !!(z.colors && z.colors.length);
        return !(z.colorMode === 'none' || z.color === null || z.color === undefined);
    }
    api.fracture = function () {
        var fn = window.fractureThisPaint;
        if (typeof fn !== 'function') return;
        if (off()) return fn();
        var zs = null; try { zs = zones; } catch (_) {}
        if (!zs || !zs.length) return fn();                       // the original says "add a zone first"
        var idx = 0; try { if (typeof selectedZoneIndex === 'number' && selectedZoneIndex >= 0 && selectedZoneIndex < zs.length) idx = selectedZoneIndex; } catch (_) {}
        var z = zs[idx] || {}, name = z.name || ('Zone ' + (idx + 1));
        var locked = false; try { locked = (typeof window._spbColorLocked === 'function' && window._spbColorLocked()) || !!z.lockBaseColor; } catch (_) {}
        var empty = !zoneCovers(z);
        var lines = [
            'This gives "' + name + '" the Soul Core Emerald material with Pink Flash, replacing the material it has now.',
            locked ? 'Its base colour stays, because Color Lock is on.' : 'Its base colour changes too.',
            'Ctrl+Z undoes it.'
        ];
        return confirmDialog({
            title: 'Fracture "' + name + '"?', lines: lines, thumb: '/thumbnails/monolithic/fs_core_emerald.png',
            warn: empty ? 'Nothing on the car will change yet: "' + name + '" does not cover any part of the car. Pick a colour or draw an area for it first (Pick Color from Car), or choose a zone that already has paint.' : '',
            okLabel: empty ? 'Apply anyway' : 'Fracture it', cancelLabel: 'Cancel', focusCancel: empty
        }).then(function (yes) { if (yes) fn(); return yes; });
    };

    /* ---- #12 / #3 launcher buttons answer the click at once (busy state + a one-line note) -------------------------------------------- */
    function opening(btn, what) {
        ensureStyle();
        if (btn && btn.__nuqBusy) return false;
        toast('Opening ' + what + '...');
        if (btn) {
            btn.__nuqBusy = true;
            var html = btn.innerHTML, w = btn.offsetWidth;
            btn.style.width = w + 'px'; btn.style.whiteSpace = 'nowrap'; btn.classList.add('spb-nuq-busy'); btn.setAttribute('aria-busy', 'true');
            if (!btn.children.length) btn.textContent = 'Opening...';
            setTimeout(function () {
                btn.classList.remove('spb-nuq-busy'); btn.removeAttribute('aria-busy'); btn.style.width = ''; btn.style.whiteSpace = ''; btn.__nuqBusy = false;
                if (btn.innerHTML !== html) btn.innerHTML = html;
            }, 3500);
        }
        return true;
    }
    api.openShokkDrop = function (btn) {
        if (off() || typeof window.openShokkDropLab !== 'function') { if (typeof window.openShokkDropLab === 'function') window.openShokkDropLab(); return; }
        if (!opening(btn, 'Shokk Drop')) return;
        setTimeout(function () { window.openShokkDropLab(); }, 40);
    };
    var _sculpt = api.openSpecSculpt;
    api.openSpecSculpt = function (btn) {
        if (off()) return _sculpt();
        if (!opening(btn, 'Spec Sculpt')) return;
        setTimeout(_sculpt, 40);
    };

    /* ---- #14 notices: short-lived, click-through; Esc closes the windows that had no Esc ------------------------------------------------ */
    (function wrapToast() {
        var orig = window.showToast;
        if (typeof orig !== 'function' || orig.__nuq) return;
        var wrapped = function (msg, isError, details) {
            var r = orig.apply(this, arguments);
            if (off()) return r;
            try {
                var el = doc.getElementById('toast'), len = String(msg == null ? '' : msg).length + (details ? String(details).length : 0);
                var bad = !!(el && /\b(error|warning)\b/.test(el.className));
                clearTimeout(wrapped._timer);
                wrapped._timer = setTimeout(function () { var t = doc.getElementById('toast'); if (t) t.className = 'toast'; }, bad ? Math.min(15000, 6000 + 60 * len) : Math.min(10000, 3500 + 45 * len));
            } catch (_) {}
            return r;
        };
        wrapped.__nuq = true; wrapped._timer = orig._timer;
        window.showToast = wrapped;
    })();
    if (!off()) ensureStyle();
    function shown(e) { if (!e) return false; var cs = window.getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
    function openWindows() {
        var c = [], e = doc.getElementById('spbProjectsModal');
        if (shown(e)) c.push({ z: 100090, close: (function (m) { return function () { m.remove(); }; })(e) });
        e = doc.getElementById('filePickerOverlay');
        if (e && e.classList.contains('active') && shown(e)) c.push({ z: 1100, close: (function (m) { return function () { if (typeof window.closeFilePicker === 'function') window.closeFilePicker(); else m.classList.remove('active'); }; })(e) });
        e = doc.getElementById('layerActionsMenu');
        if (shown(e)) c.push({ z: 900, close: (function (m) { return function () { m.style.display = 'none'; var b = doc.getElementById('layerActionsMenuBtn'); if (b) b.setAttribute('aria-expanded', 'false'); }; })(e) });
        c.sort(function (a, b) { return b.z - a.z; });
        return c;
    }
    doc.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Escape' || off()) return;
        var snap = openWindows(); if (!snap.length) return;
        setTimeout(function () {                    // after every other Esc handler has had its turn
            if (ev.defaultPrevented) return;
            var now = openWindows(); if (now.length < snap.length) return;     // something else already closed a window
            try { snap[0].close(); } catch (_) {}
        }, 0);
    }, false);

    window.SpbNuq = api;
})();
