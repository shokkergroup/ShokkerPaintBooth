/* [SPB-POLISH-G 2026-10-10] The canvas column owns the space.
   Lane POLISH-G, owner: "MAKING the UI/UX look like a REAL PRODUCT and not as vibecoded as we look now."
   Before: at the 1100x800 minimum window the centre column is ~392px, so SOURCE and LIVE PREVIEW were two 183px squares with ~150-200px of dead
   space under them (and the 10 percent Fit floor clipped the source canvas inside a 183px pane).
   G-1  A pane header row (#spbPgHead, first child of #splitViewContainer) with a segmented control  Split | Source | Preview.  The panes are sized
        to the largest square that fits the width AND the height of #previewSquaresRow (its own flex box, which never depends on the squares, so there
        is no feedback loop).  Choice is remembered per viewer (localStorage, in try/catch).  Auto (no stored choice): Split at >=1400px wide; below
        1400 Split only if both squares can be >=300px, otherwise Source.  Key:  \  cycles Split > Source > Preview (not used by any other handler).
        The hidden pane keeps its box (visibility:hidden, out of flow) so Fit, hit-testing and the preview refresh stay valid.  Clicking a spec chip in
        Source mode shows the Preview (the chip would otherwise change something you cannot see).  In Source mode the pane header carries its own
        Refresh button (the pane's own Refresh lives inside the hidden Live Preview pane).
   G-2  Side panels: the old collapse handles did nothing visible (the panel widths are !important in CSS).  Now: the Zone Popout Panel and the Layers
        panel collapse to a slim rail (icon + title) that reopens on click; the existing handles, Shift+E and the expand tab all go through the same
        toggle.  Below 1280px the Zone Popout Panel starts collapsed unless the viewer chose otherwise (remembered).  Transition 120ms fade, the
        centre column snaps in the same frame (no animated reflow of the canvas).
   G-3  The "Painting layer: ..." banner (#drawZoneIndicator) is MOVED (same node, same handlers, same x) into the pane header row and styled as a
        compact chip; full text in its tooltip.
   Kill switch: document.body.classList.add('spb-polish-g-off') (CSS block [SPB-POLISH-G] is gated by it; this script moves the banner back and hides
   the new nodes).  window.SPB_POLISH_G_OFF = true before load disables the script.  Styled by the [SPB-POLISH-G] block at the end of
   css/spb-clean-default-20260829.css.  Public hooks for tests: window.__spbPolishG. */
(function () {
    'use strict';
    if (window.__spbPolishG || window.SPB_POLISH_G_OFF) return;
    var doc = document;
    var K_MODE = 'spb.pg.mode', K_POP = 'spb.pg.pop', K_LAY = 'spb.pg.lay';
    var GAP = 8, MIN_PANE = 120, SPLIT_MIN = 300, WIDE = 1400, POP_AUTO_W = 1280, BAR_FULL_W = 970;   // [S13 2026-10-12 owner: "lose this vibecoded look"] was 800; now only the FALLBACK. The real threshold is measured in barNeed() (the three groups need ~969px in one row at 100% UI scale).
    var st = { mode: null, tmp: null, pop: null, lay: null, W: 0, H: 0, s: 0, eff: '', built: false };
    var head = null, seg = null, refreshBtn = null, popRail = null, layRail = null, home = null, moBan = null, ro = null, fitRaf = 0, animT = 0;

    function $(id) { return doc.getElementById(id); }
    function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { } }
    function off() { var c = doc.body && doc.body.classList; return !!c && (c.contains('spb-polish-g-off') || c.contains('spb-polish-off')); }
    function clean(v, ok) { return ok.indexOf(v) >= 0 ? v : null; }

    st.mode = clean(lsGet(K_MODE), ['split', 'source', 'preview']);
    st.pop = clean(lsGet(K_POP), ['open', 'closed']);
    st.lay = clean(lsGet(K_LAY), ['open', 'closed']);

    // ---- icons: one monochrome line set (24px grid, 1.75 stroke), same family as the toolbar --------------------------------------------------------------
    var ICON = {
        split: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="8" height="14" rx="1.6"/><rect x="13" y="5" width="8" height="14" rx="1.6"/></svg>',
        source: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16M10 4v16"/></svg>',
        preview: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/></svg>',
        refresh: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 0 0-14.6-4.4M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.6 4.4M20 20v-4h-4"/></svg>',
        zones: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
        layers: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5 3 8.5l9 5 9-5-9-5z"/><path d="m3 13 9 5 9-5"/></svg>'
    };
    var LABEL = { split: 'Split', source: 'Source', preview: 'Preview' };
    var TIP = {
        split: 'Split: Source and Live Preview side by side',
        source: 'Source: one big Source pane to paint on',
        preview: 'Live Preview: one big Live Preview pane'
    };

    // ---- G-1: modes + sizing ------------------------------------------------------------------------------------------------------------------------------
    function splitSize() { return Math.floor(Math.min((st.W - GAP) / 2, st.H)); }
    function oneSize() { return Math.floor(Math.min(st.W, st.H)); }
    function autoMode() {
        if (window.innerWidth >= WIDE) return 'split';
        return (st.W > 0 && st.H > 0 && splitSize() >= SPLIT_MIN) ? 'split' : 'source';
    }
    function effMode() { return st.tmp || st.mode || autoMode(); }

    function cont() { return $('splitViewContainer'); }
    function rowBox() {
        var row = $('previewSquaresRow'); if (!row) return false;
        var cs = getComputedStyle(row);
        var pl = parseFloat(cs.paddingLeft) || 0, pr = parseFloat(cs.paddingRight) || 0, pt = parseFloat(cs.paddingTop) || 0, pb = parseFloat(cs.paddingBottom) || 0;
        st.W = Math.max(0, row.clientWidth - pl - pr);
        st.H = Math.max(0, row.clientHeight - pt - pb);
        return true;
    }
    // G-4: below ~800px the RENDER / eyedropper / zoom bar wraps to 2-3 rows at three different heights (39 / 36 / 32px). The class puts RENDER + zoom on one row at 36px
    // each and the eyedropper dock under it (CSS in the POLISH-G block), which hands 50px of height back to the panes.
    // [S13 2026-10-12 owner: "lose this vibecoded look"] BAR_FULL_W was a fixed 800, but RENDER (254) + colour dock (~384) + zoom (~295) + gaps + padding need ~969px in ONE row. Between 800 and ~970px of bar width (windows of about 1700-1850px
    // with the zone editor open) the row was NOT compact yet the dock's buttons wrapped into a hidden 2nd row, clipped under the 56px bar. The threshold is now MEASURED: the natural (max-content) width of
    // the visible groups with the compact class off, so UI scale, a longer colour readout or a changed caption move it by themselves. All inline styles are restored in the same frame (no paint between).
    function barNeed(bar) {
        var hadC = bar.classList.contains('spb-pg-barc'), kids = [], saved = [], i, k, sum = 0, cs, need;
        if (hadC) bar.classList.remove('spb-pg-barc');
        cs = getComputedStyle(bar);
        for (i = 0; i < bar.children.length; i++) {
            k = bar.children[i];
            if (getComputedStyle(k).display === 'none') continue;
            kids.push(k); saved.push(k.getAttribute('style'));
        }
        for (i = 0; i < kids.length; i++) {
            kids[i].style.setProperty('flex', '0 0 auto', 'important');
            kids[i].style.setProperty('width', 'max-content', 'important');
            kids[i].style.setProperty('max-width', 'none', 'important');
        }
        for (i = 0; i < kids.length; i++) sum += kids[i].offsetWidth;
        for (i = 0; i < kids.length; i++) { if (saved[i] === null) kids[i].removeAttribute('style'); else kids[i].setAttribute('style', saved[i]); }
        if (hadC) bar.classList.add('spb-pg-barc');
        if (!kids.length) return 0;
        need = sum + (kids.length - 1) * (parseFloat(cs.columnGap) || parseFloat(cs.gap) || 0) + (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
        return Math.ceil(need) + 2;
    }
    function applyBar() {
        var bar = $('previewBottomBar'); if (!bar) return;
        if (off()) { bar.classList.remove('spb-pg-barc'); return; }
        var w = bar.clientWidth; if (w < 50) return;
        bar.classList.toggle('spb-pg-barc', w < (barNeed(bar) || BAR_FULL_W));
    }
    function applyMode() {
        var c = cont(); if (!c || !head) return;
        applyBar();
        if (off()) { c.classList.remove('spb-pg-on', 'spb-pg-split', 'spb-pg-source', 'spb-pg-preview', 'spb-pg-compact'); c.style.removeProperty('--pg-s'); return; }
        if (!rowBox() || st.W < 40 || st.H < 40) return;
        var m = effMode();
        var s = Math.max(MIN_PANE, m === 'split' ? splitSize() : oneSize());
        var changed = (s !== st.s) || (m !== st.eff);
        st.s = s; st.eff = m;
        c.classList.add('spb-pg-on');
        ['split', 'source', 'preview'].forEach(function (k) { c.classList.toggle('spb-pg-' + k, k === m); });
        c.style.setProperty('--pg-s', s + 'px');
        c.classList.toggle('spb-pg-compact', s < 420);
        var btns = seg.querySelectorAll('button[data-mode]');
        for (var i = 0; i < btns.length; i++) {
            var on = btns[i].getAttribute('data-mode') === m;
            btns[i].classList.toggle('on', on);
            btns[i].setAttribute('aria-checked', on ? 'true' : 'false');
            btns[i].tabIndex = on ? 0 : -1;
        }
        if (refreshBtn) refreshBtn.hidden = (m !== 'source');
        if (changed) scheduleFit();
    }
    function setMode(m, persist) {
        if (!LABEL[m]) return;
        if (persist === false) { st.tmp = m; } else { st.tmp = null; st.mode = m; lsSet(K_MODE, m); }
        applyMode();
    }
    function cycleMode() {
        var order = ['split', 'source', 'preview'];
        setMode(order[(order.indexOf(effMode()) + 1) % 3]);
    }
    // Fit only when the view is still AT Fit (same rule as TFX1 TA-021): a view the painter zoomed by hand is left alone, but re-centred.
    function scheduleFit() {
        if (fitRaf) return;
        fitRaf = requestAnimationFrame(function () {
            fitRaf = 0;
            try {
                if (typeof freeTransformState !== 'undefined' && freeTransformState) return;
                var atFit = (typeof window.__spbFitZoom !== 'number') || (typeof currentZoom === 'number' && Math.abs(currentZoom - window.__spbFitZoom) <= 0.004);
                if (atFit && typeof canvasZoom === 'function') canvasZoom('fit');
                else if (typeof applyZoom === 'function') applyZoom();
            } catch (e) { }
        });
    }

    // ---- G-3: the banner becomes a chip in the pane header row ---------------------------------------------------------------------------------------------
    function chipText(b) {
        var l = $('drawZoneLabel'), n = $('drawZoneName'), h = $('drawZoneHint');
        var t = [l && l.textContent, n && n.textContent, h && h.textContent].map(function (x) { return (x || '').replace(/\s+/g, ' ').trim(); }).filter(Boolean).join(' ');
        return t;
    }
    function syncChip() {
        var b = $('drawZoneIndicator'); if (!b) return;
        var t = chipText(b);
        if (t && b.getAttribute('data-pg-title') !== t) { b.setAttribute('data-pg-title', t); b.title = t; }
    }
    function placeBanner() {
        var b = $('drawZoneIndicator'); if (!b || !head) return;
        if (!home) home = { parent: b.parentNode, next: b.nextSibling };
        if (off()) {
            if (b.parentNode === head && home.parent) { home.parent.insertBefore(b, (home.next && home.next.parentNode === home.parent) ? home.next : null); }
            b.classList.remove('spb-pg-chip');
        } else if (b.parentNode !== head) {
            head.appendChild(b); b.classList.add('spb-pg-chip');
        }
        if (!moBan && window.MutationObserver) {
            moBan = new MutationObserver(syncChip);
            moBan.observe(b, { childList: true, characterData: true, subtree: true });
        }
        syncChip();
    }

    // ---- G-2: side panels collapse to a rail ---------------------------------------------------------------------------------------------------------------
    function effPop() { return st.pop || (window.innerWidth < POP_AUTO_W ? 'closed' : 'open'); }
    function effLay() { return st.lay || 'open'; }
    function flashAnim() {
        var b = doc.body; b.classList.add('spb-pg-anim');
        clearTimeout(animT); animT = setTimeout(function () { b.classList.remove('spb-pg-anim'); }, 180);
    }
    function applyPanels(animate) {
        var b = doc.body; if (!b) return;
        var po = effPop() === 'closed', lo = effLay() === 'closed';
        if (animate) flashAnim();
        b.classList.toggle('spb-pg-pop-closed', po);
        b.classList.toggle('spb-pg-lay-closed', lo);
        if (popRail) popRail.setAttribute('aria-expanded', 'false');
        var hl = $('leftCollapseBtn'), hr = $('rightCollapseBtn');
        if (hl) { hl.title = 'Collapse the zone editor to a rail'; hl.setAttribute('aria-label', 'Collapse the zone editor'); hl.setAttribute('aria-expanded', po ? 'false' : 'true'); }
        if (hr) { hr.title = 'Collapse the Layers panel to a rail'; hr.setAttribute('aria-label', 'Collapse the Layers panel'); hr.setAttribute('aria-expanded', lo ? 'false' : 'true'); }
        applyMode();
    }
    function togglePop() { st.pop = (effPop() === 'closed') ? 'open' : 'closed'; lsSet(K_POP, st.pop); applyPanels(true); }
    function toggleLay() { st.lay = (effLay() === 'closed') ? 'open' : 'closed'; lsSet(K_LAY, st.lay); applyPanels(true); }
    function mkRail(id, cls, icon, title, tip, onclick) {
        var b = doc.createElement('button'); b.type = 'button'; b.id = id; b.className = 'spb-pg-rail ' + cls;
        b.title = tip; b.setAttribute('aria-label', tip); b.setAttribute('aria-expanded', 'false');
        b.innerHTML = icon + '<span class="spb-pg-rail-t">' + title + '</span>';
        b.addEventListener('click', onclick);
        return b;
    }
    function buildRails() {
        if (popRail) return;
        var main = doc.querySelector('.main-container'), center = $('centerPanel'), right = $('rightPanel');
        if (!main || !center || !right) return;
        popRail = mkRail('spbPgPopRail', 'spb-pg-rail-l', ICON.zones, 'Zone editor', 'Open the zone editor (Shift+E)', function () { togglePop(); });
        main.insertBefore(popRail, center);
        layRail = mkRail('spbPgLayRail', 'spb-pg-rail-r', ICON.layers, 'Layers', 'Open the Layers panel', function () { toggleLay(); });
        if (right.nextSibling) main.insertBefore(layRail, right.nextSibling); else main.appendChild(layRail);
    }
    function hookGlobals() {
        var tpc = window.togglePanelCollapse, tzf = window.toggleZoneFloat;
        window.togglePanelCollapse = function (side) {
            if (off()) return tpc ? tpc.apply(this, arguments) : undefined;
            if (side === 'left') return togglePop();
            if (side === 'right') return toggleLay();
            return tpc ? tpc.apply(this, arguments) : undefined;
        };
        window.toggleZoneFloat = function () {
            var f = $('zoneEditorFloat');
            if (off()) return tzf ? tzf.apply(this, arguments) : undefined;
            if (!f || !f.classList.contains('active')) return;
            togglePop();
        };
    }

    // ---- header row + wiring -------------------------------------------------------------------------------------------------------------------------------
    function buildHead() {
        var c = cont();
        if (!c || !c.classList.contains('spb-unified') || !$('previewSquaresRow')) return false;
        if (head) return true;
        head = doc.createElement('div'); head.id = 'spbPgHead'; head.className = 'spb-pg-head';
        seg = doc.createElement('div'); seg.className = 'spb-pg-seg'; seg.setAttribute('role', 'radiogroup'); seg.setAttribute('aria-label', 'Pane layout');
        ['split', 'source', 'preview'].forEach(function (m) {
            var b = doc.createElement('button'); b.type = 'button'; b.setAttribute('data-mode', m); b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', 'false');
            b.title = TIP[m] + '  (\\ cycles the three)'; b.setAttribute('aria-label', TIP[m]);
            b.innerHTML = ICON[m] + '<span>' + LABEL[m] + '</span>';
            b.addEventListener('click', function () { setMode(m); });
            seg.appendChild(b);
        });
        seg.addEventListener('keydown', function (e) {
            if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
            e.preventDefault();
            var order = ['split', 'source', 'preview'], i = order.indexOf(effMode());
            setMode(order[(i + (e.key === 'ArrowRight' ? 1 : 2)) % 3]);
            var on = seg.querySelector('button.on'); if (on) on.focus();
        });
        head.appendChild(seg);
        refreshBtn = doc.createElement('button'); refreshBtn.type = 'button'; refreshBtn.className = 'spb-pg-refresh'; refreshBtn.hidden = true;
        refreshBtn.title = 'Refresh Preview (F5): stops a stuck render and starts again'; refreshBtn.setAttribute('aria-label', 'Refresh the Live Preview');
        refreshBtn.innerHTML = ICON.refresh;
        refreshBtn.addEventListener('click', function () { if (typeof forcePreviewRefresh === 'function') forcePreviewRefresh(); });
        head.appendChild(refreshBtn);
        c.insertBefore(head, c.firstChild);
        placeBanner();
        // spec chips: click opens the full-view lightbox in every mode (their own onclick); the hover enlarge lands inside the Live Preview pane, so it shows in Split / Preview only
        var row = $('previewSquaresRow');
        if (window.ResizeObserver && row) { ro = new ResizeObserver(function () { applyMode(); }); ro.observe(row); }
        // [S13 2026-10-12 owner: "lose this vibecoded look"] the bar's own box + its content decide the single-row threshold now (barNeed), so watch them too (rAF-debounced; the measure restores everything it touches, so no feedback loop)
        var barEl = $('previewBottomBar');
        if (barEl && !barEl.__spbPgWatch) {
            barEl.__spbPgWatch = true;
            if (window.ResizeObserver && ro) ro.observe(barEl);
            if (window.MutationObserver) {
                var barRaf = 0;
                new MutationObserver(function () { if (barRaf) return; barRaf = requestAnimationFrame(function () { barRaf = 0; applyBar(); }); }).observe(barEl, { childList: true, characterData: true, subtree: true });
            }
        }
        return true;
    }
    function onKey(e) {
        if (off() || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key !== '\\') return;
        var t = e.target, tg = t && t.tagName;
        if (tg === 'INPUT' || tg === 'TEXTAREA' || tg === 'SELECT' || (t && t.isContentEditable)) return;
        e.preventDefault(); cycleMode();
    }
    function watchOff() {
        if (!window.MutationObserver || !doc.body) return;
        var last = off();
        new MutationObserver(function () {
            var now = off(); if (now === last) return; last = now;
            placeBanner(); applyPanels(false); applyMode();
        }).observe(doc.body, { attributes: true, attributeFilter: ['class'] });
    }
    function start() {
        hookGlobals(); buildRails(); applyPanels(false); watchOff();
        doc.addEventListener('keydown', onKey);
        window.addEventListener('resize', function () { applyPanels(false); });
        var tries = 0;
        (function tryHead() {
            if (buildHead()) { applyMode(); return; }
            if (++tries < 80) setTimeout(tryHead, 250);
        })();
    }
    window.__spbPolishG = {
        version: 1,
        state: function () { return { mode: st.mode, tmp: st.tmp, eff: effMode(), pop: effPop(), lay: effLay(), W: st.W, H: st.H, s: st.s, splitS: splitSize(), oneS: oneSize() }; },
        clearTmp: function () { if (st.tmp) { st.tmp = null; applyMode(); } },   // [TICKETS-4 2026-10-10 item 3] hand a temporary view (setMode(m, false)) back to the stored / auto choice
        setMode: setMode, cycleMode: cycleMode, togglePop: togglePop, toggleLay: toggleLay, apply: function () { applyPanels(false); },
        reset: function () { st.mode = st.tmp = st.pop = st.lay = null; lsSet(K_MODE, null); lsSet(K_POP, null); lsSet(K_LAY, null); applyPanels(false); }
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
})();
