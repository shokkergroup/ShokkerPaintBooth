/* ==========================================================================================================================================================
   SPB LAYOUT RESIZE  2026-10-12  (lane S16)   [S16 2026-10-12 owner: resizable panels + bigger canvas]
   Owner: "make the SOURCE, LIVE PREVIEW, COMBINED, METAL, ROUGH, COAT all a bit bigger in the middle ... if people could drag around and resize various things on the screen the
   way they like it then they could customize it".
   What this does (the DEFAULT sizes live in css/spb-skin-detail-20261012.css, block S16; this file only adds the interactive part):
     1. Three splitters (Zones list | Zone editor, Zone editor | centre, centre | Layers). Pointer drag, keyboard (focus a splitter, Left/Right = 16px, Shift = 48px, Home/End = min/max),
        double-click = reset that one panel to its default.  They hide while their panel is collapsed (the existing arrows / rails keep working).
     2. Widths are CSS variables on <html> (--s16-left / --s16-zone / --s16-right).  Dragging sets them, reset removes them (= the stylesheet defaults).  Saved in
        localStorage 'spb_layout_v1' ({left, zone, right}, only what the user changed).  "Reset layout" (Settings panel) clears it.
     3. The four channel tiles (Combined / R Metal / G Rough / B Coat) are square; their side (--s16-tile) is the room left under the two preview squares, so the squares never shrink
        for the tiles, and the tiles never leave the view at 1100x800.
     4. After every layout change the centre column re-fits ONCE per animation frame, with a timer fallback (rAF is paused in hidden / occluded windows).  The squares themselves are
        sized by spb-polish-g (--pg-s = min((rowW-8)/2, rowH)): a square box that is letterboxed, never stretched.
   KILL SWITCH: localStorage SPB_RESIZE_OFF='1'  -> html.spb-resize-off, no splitters, pre-S16 layout (the CSS in block S16 is scoped :not(.spb-resize-off)).
   Public hooks: window.SPB_LAYOUT = { state(), set(key, px), reset(key?), place() }.   Nothing here touches the render path, the canvases' content or any saved project data.
   ========================================================================================================================================================== */
(function () {
    'use strict';
    var doc = document, root = doc.documentElement;
    var KEY = 'spb_layout_v1';
    try { if (localStorage.getItem('SPB_RESIZE_OFF') === '1') { root.classList.add('spb-resize-off'); return; } } catch (e) { }
    if (window.SPB_LAYOUT || root.classList.contains('spb-skin-off')) return;

    // key -> css variable, limits, which side the hairline sits on, label
    var DEF = {
        left:  { v: '--s16-left',  min: 148, max: 300, step: 16, label: 'Zones list width' },
        zone:  { v: '--s16-zone',  min: 300, max: 680, step: 16, label: 'Zone editor width' },
        right: { v: '--s16-right', min: 200, max: 480, step: 16, label: 'Layers panel width' }
    };
    var MIN_CENTER = 420;                   // the centre column (squares + tiles) never gets narrower than this because of a drag
    var TILE_MIN = 48, TILE_MAX = 150, GAP = 8;
    var st = load();                        // user-changed widths only
    var bars = {};                          // key -> element
    var drag = null, raf = 0, tmr = 0, tileLast = -1, lastPlaceSig = '', verifyT = 0;

    function $(id) { return doc.getElementById(id); }
    function load() {
        var o = {};
        try {
            var j = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
            Object.keys(DEF).forEach(function (k) { var n = Number(j[k]); if (isFinite(n) && n >= DEF[k].min && n <= DEF[k].max) o[k] = Math.round(n); });
        } catch (e) { }
        return o;
    }
    function save() {
        try {
            if (Object.keys(st).length) localStorage.setItem(KEY, JSON.stringify(st)); else localStorage.removeItem(KEY);
        } catch (e) { }
    }
    function shown(el) { return !!el && el.offsetWidth > 0 && el.offsetHeight > 0 && getComputedStyle(el).display !== 'none'; }
    function widthOf(key) {
        var el = key === 'left' ? $('leftPanel') : key === 'zone' ? $('zoneEditorFloat') : $('rightPanel');
        return el && shown(el) ? Math.round(el.getBoundingClientRect().width) : 0;
    }
    function setVar(key, px) { root.style.setProperty(DEF[key].v, Math.round(px) + 'px'); }
    function clearVar(key) { root.style.removeProperty(DEF[key].v); }
    function centreW() { var c = $('splitViewContainer'); return c ? c.offsetWidth : 0; }

    // ---------------------------------------------------------------- apply stored widths (clamped to the window) ----
    function applyStored() {
        Object.keys(DEF).forEach(function (k) {
            if (st[k] == null) { clearVar(k); return; }
            setVar(k, Math.max(DEF[k].min, Math.min(DEF[k].max, st[k])));
        });
        guardBudget();
    }
    // a smaller window than the one the widths were saved in: pull the saved widths in so the centre column keeps its minimum (not persisted)
    function guardBudget() {
        var cw = centreW(); if (!cw || drag) return;
        var deficit = MIN_CENTER - cw; if (deficit <= 0) return;
        ['zone', 'right', 'left'].forEach(function (k) {
            if (deficit <= 0 || st[k] == null) return;
            var cur = widthOf(k) || st[k], take = Math.min(Math.max(0, cur - DEF[k].min), deficit);
            if (take > 0) { setVar(k, cur - take); deficit -= take; }
        });
    }

    // ---------------------------------------------------------------- splitters ----
    function mk(key, side, label) {
        var b = doc.createElement('div');
        b.className = 'spb-rsz'; b.setAttribute('data-k', key); b.setAttribute('data-side', side); b.hidden = true;
        b.setAttribute('role', 'separator'); b.setAttribute('aria-orientation', 'vertical'); b.tabIndex = 0;
        b.setAttribute('aria-label', label + ' (drag, or use Left / Right arrow keys; double-click to reset)');
        b.title = label + ': drag to resize, double-click to reset';
        b.addEventListener('pointerdown', onDown);
        b.addEventListener('keydown', onKey);
        b.addEventListener('dblclick', function (e) { e.preventDefault(); reset(key); });
        doc.body.appendChild(b);
        bars[key] = b;
        return b;
    }
    function build() {
        if (bars.left) return;
        mk('left', 'l', DEF.left.label);        // Zones list | Zone editor   (hairline on the left edge of its 8px box = the list's right border)
        mk('zone', 'l', DEF.zone.label);        // Zone editor | centre
        mk('right', 'r', DEF.right.label);      // centre | Layers            (hairline on the right edge = the Layers panel's left border)
    }
    function setBar(key, on, x, top, h) {
        var b = bars[key]; if (!b) return;
        if (!on) { if (!b.hidden) b.hidden = true; return; }
        b.hidden = false;
        b.style.left = Math.round(x) + 'px'; b.style.top = Math.round(top) + 'px'; b.style.height = Math.max(0, Math.round(h)) + 'px';
        var w = widthOf(key), lim = limits(key);
        b.setAttribute('aria-valuemin', String(lim[0])); b.setAttribute('aria-valuemax', String(lim[1])); b.setAttribute('aria-valuenow', String(w));
    }
    function place() {
        build();
        var L = $('leftPanel'), Z = $('zoneEditorFloat'), R = $('rightPanel');
        var ls = shown(L), zs = shown(Z), rs = shown(R);
        var lr = ls ? L.getBoundingClientRect() : null, zr = zs ? Z.getBoundingClientRect() : null, rr = rs ? R.getBoundingClientRect() : null;
        var top = (lr || rr || zr) ? (lr || rr || zr).top : 0, h = (lr || rr || zr) ? (lr || rr || zr).height : 0;
        setBar('left', ls, lr ? lr.right - 1 : 0, top, h);
        setBar('zone', zs, zr ? zr.right - 1 : 0, zr ? zr.top : top, zr ? zr.height : h);
        setBar('right', rs, rr ? rr.left - 7 : 0, top, h);
    }
    // min / max for one panel right now: the centre column keeps MIN_CENTER
    function limits(key) {
        var d = DEF[key], cur = widthOf(key) || d.min, cw = centreW();
        var room = cw ? cur + (cw - MIN_CENTER) : d.max;
        return [d.min, Math.max(d.min, Math.min(d.max, Math.round(room)))];
    }

    // ---------------------------------------------------------------- interaction ----
    // Moves / release are listened for on the document (capture phase), NOT only on the splitter: pointer capture is requested too, but when it is not granted or is dropped
    // (a synthetic mouse, a window that loses focus) the drag must still follow the pointer.  A move with no button down ends the drag (mouse released outside the window).
    function onDown(e) {
        if (e.button != null && e.button !== 0) return;
        if (drag) onUp();
        var key = e.currentTarget.getAttribute('data-k');
        e.preventDefault();
        drag = { key: key, x0: e.clientX, w0: widthOf(key), lim: limits(key), id: e.pointerId, el: e.currentTarget };
        try { drag.el.setPointerCapture(e.pointerId); } catch (_) { }
        drag.el.classList.add('s16-on'); root.classList.add('s16-drag');
        doc.addEventListener('pointermove', onMove, true);
        doc.addEventListener('pointerup', onUp, true);
        doc.addEventListener('pointercancel', onUp, true);
        window.addEventListener('blur', onUp);
    }
    function onMove(e) {
        if (!drag) return;
        if (e.pointerId !== drag.id) return;
        if (e.buttons === 0) { onUp(); return; }
        var dx = e.clientX - drag.x0, dir = drag.key === 'right' ? -1 : 1;
        var v = Math.max(drag.lim[0], Math.min(drag.lim[1], drag.w0 + dir * dx));
        setVar(drag.key, v); st[drag.key] = Math.round(v);
        sched();
    }
    function onUp() {
        if (!drag) return;
        var el = drag.el;
        doc.removeEventListener('pointermove', onMove, true); doc.removeEventListener('pointerup', onUp, true); doc.removeEventListener('pointercancel', onUp, true);
        window.removeEventListener('blur', onUp);
        try { el.releasePointerCapture(drag.id); } catch (_) { }
        el.classList.remove('s16-on'); root.classList.remove('s16-drag');
        drag = null; save(); run();
    }
    function onKey(e) {
        var key = e.currentTarget.getAttribute('data-k'), d = DEF[key], lim = limits(key), cur = widthOf(key) || d.min, v = null;
        var dir = key === 'right' ? -1 : 1, step = e.shiftKey ? d.step * 3 : d.step;
        if (e.key === 'ArrowLeft') v = cur - dir * step;
        else if (e.key === 'ArrowRight') v = cur + dir * step;
        else if (e.key === 'Home') v = lim[0];
        else if (e.key === 'End') v = lim[1];
        else if (e.key === 'Enter') { reset(key); e.preventDefault(); return; }
        if (v == null) return;
        e.preventDefault();
        v = Math.max(lim[0], Math.min(lim[1], v));
        setVar(key, v); st[key] = Math.round(v); save(); run();
    }
    function reset(key) {
        if (key) { delete st[key]; clearVar(key); } else { st = {}; Object.keys(DEF).forEach(clearVar); }
        save(); run();
        // the widths changed under the layout observers: re-run once more after the layout settles
        setTimeout(run, 80);
    }

    // ---------------------------------------------------------------- the four channel tiles ----
    function fitTile() {
        var strip = $('previewTopStrip'), row = $('previewSquaresRow'), cont = $('splitViewContainer');
        if (!strip || !row || !cont) return;
        var stripH = strip.offsetHeight; if (stripH < 8) return;                       // dock hidden (no spec map yet)
        var cs = getComputedStyle(row);
        var W = row.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
        var H = row.clientHeight - (parseFloat(cs.paddingTop) || 0) - (parseFloat(cs.paddingBottom) || 0);
        if (W < 80 || H < 40) return;
        var cv = strip.querySelector('.spec-channel-dock-canvas');
        var chrome = cv ? stripH - cv.getBoundingClientRect().height : 34;             // label + paddings around the tile
        var eff = 'split';
        try { if (window.__spbPolishG) eff = window.__spbPolishG.state().eff || 'split'; } catch (_) { }
        var focus = cont.classList.contains('spb-focus-source');
        var want = (eff === 'split' && !focus) ? Math.floor((W - GAP) / 2) : W;        // the square(s) get their room first; one big pane wants everything
        var spare = stripH + H - want - 6;                                             // strip + row is constant while the tile changes, so this cannot oscillate
        var byW = Math.floor((strip.clientWidth - 16 - GAP * 3) / 4);
        var t = Math.round(Math.max(TILE_MIN, Math.min(TILE_MAX, spare - chrome, byW)));
        if (t !== tileLast) { tileLast = t; root.style.setProperty('--s16-tile', t + 'px'); }
    }

    // ---------------------------------------------------------------- one re-fit per frame (+ timer fallback) ----
    function atFit() {
        try { return (typeof window.__spbFitZoom !== 'number') || (typeof currentZoom === 'number' && Math.abs(currentZoom - window.__spbFitZoom) <= 0.004); } catch (e) { return true; }
    }
    function refitCanvas() {
        try {
            if (typeof freeTransformState !== 'undefined' && freeTransformState) return;
            if (atFit() && typeof window.canvasZoom === 'function') window.canvasZoom('fit');
            else if (typeof window.applyZoom === 'function') window.applyZoom();
        } catch (e) { }
    }
    function sched() {
        if (raf || tmr) return;
        if (typeof requestAnimationFrame === 'function') raf = requestAnimationFrame(run);
        tmr = setTimeout(run, 50);                                                    // rAF is paused in a hidden / occluded window
    }
    function run() {
        if (raf) { try { cancelAnimationFrame(raf); } catch (_) { } raf = 0; }
        if (tmr) { clearTimeout(tmr); tmr = 0; }
        try {
            if (!drag) guardBudget();
            root.classList.toggle('s16-lw', widthOf('left') >= 176);                      // wide Zones list: the original two-row zone card is used again (CSS block S16)
            place(); fitTile();
            var f = window._sizePreviewSquares; if (typeof f === 'function') f();          // memoised: no-op unless the square's side changed
            clearTimeout(verifyT); verifyT = setTimeout(verify, 90);                       // once the layout has been quiet for 90ms (also the end of a drag)
        } catch (e) { }
    }
    // spb-polish-g re-sizes the squares from its own ResizeObserver (--pg-s) and re-fits the canvas on rAF.  Neither fires in a hidden / occluded window, so, once the layout is quiet:
    // make sure polish-g has measured the current row (apply() only when it has not caught up: it costs ~50ms), then fit the source canvas if the square's side changed.
    function verify() {
        try {
            var g = window.__spbPolishG, row = $('previewSquaresRow');
            if (g && row && typeof g.state === 'function') {
                var s = g.state();
                if (Math.abs(s.W - row.clientWidth) > 24 || Math.abs(s.H - row.clientHeight) > 24) g.apply();
            }
            place(); fitTile();
            var sq = $('splitSource'), side = sq ? sq.offsetWidth : 0, sig = side + ':' + (row ? row.clientWidth : 0);
            if (side && sig !== lastPlaceSig) { lastPlaceSig = sig; refitCanvas(); }
        } catch (e) { }
    }
    function widthSig() { var r = $('previewSquaresRow'); return r ? (r.clientWidth + 'x' + r.clientHeight + ':' + tileLast) : ''; }

    // ---------------------------------------------------------------- selected channel tile + Settings button ----
    function markSel(ch) {
        var cells = doc.querySelectorAll('#specChannelDock .spec-channel-dock-cell');
        for (var i = 0; i < cells.length; i++) cells[i].classList.toggle('s16-sel', (cells[i].getAttribute('data-ch') || 'all') === ch);
    }
    function wireTiles() {
        var dock = $('specChannelDock'); if (!dock || dock.__s16) return !!dock;
        dock.__s16 = 1;
        dock.addEventListener('click', function (e) { var c = e.target.closest && e.target.closest('.spec-channel-dock-cell'); if (c) markSel(c.getAttribute('data-ch') || 'all'); }, true);
        var o = window.setSpecChannel;
        if (typeof o === 'function' && !o.__s16) {
            window.setSpecChannel = function (ch) { var r = o.apply(this, arguments); try { markSel(ch); } catch (_) { } return r; };
            window.setSpecChannel.__s16 = 1;
        }
        var cur = 'all'; try { if (typeof activeSpecChannel === 'string') cur = activeSpecChannel; } catch (_) { }
        markSel(cur === 'a' ? 'all' : cur);
        return true;
    }
    function settingsButton() {
        var dd = $('settingsDropdown'); if (!dd || $('s16LayoutSection')) return !!dd;
        var sec = doc.createElement('section'); sec.className = 'settings-section'; sec.id = 's16LayoutSection';
        sec.innerHTML = '<div class="settings-section-title">Layout</div>' +
            '<div style="display:flex; gap:8px; align-items:center; margin-top:4px;">' +
            '<button type="button" class="btn btn-sm" id="s16ResetLayoutBtn" style="flex:none; white-space:nowrap;" title="Put the Zones list, Zone editor and Layers panel back to their default widths">Reset layout</button>' +
            '<span style="font-size:9px; color:var(--text-dim);">Drag the edges between the panels to resize them. They are remembered.</span></div>';
        var looks = $('looksGrid'), anchor = looks && looks.closest ? looks.closest('section') : null;
        if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(sec, anchor.nextSibling); else dd.appendChild(sec);
        sec.querySelector('#s16ResetLayoutBtn').addEventListener('click', function () { reset(); try { if (typeof showToast === 'function') showToast('Layout reset to the default panel sizes.'); } catch (_) { } });
        return true;
    }

    // ---------------------------------------------------------------- observers ----
    var watched = [];
    function observe() {
        if (typeof ResizeObserver === 'undefined') return;
        if (!observe.ro) observe.ro = new ResizeObserver(function () { sched(); });
        ['leftPanel', 'zoneEditorFloat', 'centerPanel', 'rightPanel', 'splitViewContainer', 'previewSquaresRow', 'previewTopStrip'].forEach(function (id) {
            var el = $(id); if (el && watched.indexOf(el) < 0) { watched.push(el); observe.ro.observe(el); }
        });
        var main = doc.querySelector('.main-container');
        if (main && watched.indexOf(main) < 0) { watched.push(main); observe.ro.observe(main); }
    }
    function start() {
        applyStored();
        build();
        var tries = 0;
        (function poll() {
            observe(); wireTiles(); settingsButton(); sched();
            if (++tries < 80 && (!$('previewTopStrip') || !$('specChannelDock') || !$('settingsDropdown'))) setTimeout(poll, 250);
        })();
        window.addEventListener('resize', function () { sched(); setTimeout(sched, 150); });
        if (window.MutationObserver && doc.body) {
            var mo = new MutationObserver(function () { sched(); });
            mo.observe(doc.body, { attributes: true, attributeFilter: ['class'] });
            var z = $('zoneEditorFloat'); if (z) mo.observe(z, { attributes: true, attributeFilter: ['class', 'style'] });
        }
        // the dock shows up after the first render: re-fit the tiles then too
        doc.addEventListener('click', function () { setTimeout(sched, 120); }, true);
    }

    window.SPB_LAYOUT = {
        version: 1,
        state: function () { return { custom: JSON.parse(JSON.stringify(st)), left: widthOf('left'), zone: widthOf('zone'), right: widthOf('right'), centre: centreW(), tile: tileLast }; },
        set: function (key, px) { if (!DEF[key]) return; var l = limits(key); px = Math.max(l[0], Math.min(l[1], Number(px))); st[key] = Math.round(px); setVar(key, px); save(); run(); },
        reset: reset, place: place, run: run
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
})();
