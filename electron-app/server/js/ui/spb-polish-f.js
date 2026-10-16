/* [SPB-POLISH-F 2026-10-10] Tool band on ONE row (1100-1920). Priority-plus overflow: whatever menus do not fit the row fold into one "Menus" button.
   The SAME <details class="spb-tb-menu"> nodes are moved (not cloned) into the panel #spbPfMore > .spb-pf-more-pop, which lives INSIDE #spbTopToolbar, so every
   handler that delegates from the bar (js/canvas/tool-menus.js toggle / click / Esc / arrows, tool-workflow.js, ontoggle="" attributes) keeps working and the
   ids (#spbRetouchMenu, #spbRevMatMenu, #spbSymMenu ...) stay in the document. Folding goes from the right end (Adjust, Transform, Mask, ...), so the folded set
   is always a suffix of the menu order; widening the window moves them back in order. The Render History menu (right-anchored) is never folded.
   Nothing here changes a tool's behaviour. Kill switch: body.spb-polish-f-off (menus return to the row, the button hides) or body.spb-polish-off.
   Styled by the [SPB-POLISH-F] block at the end of css/spb-clean-default-20260829.css. */
(function () {
    'use strict';
    if (window.__spbPolishF) return;
    window.__spbPolishF = { version: 1, fit: function () { schedule(true); } };
    var doc = document, bar = null, wrap = null, btn = null, pop = null;
    var folded = [], busy = false, raf = 0, mo = null, lastKey = '', wantForce = false;

    function off() { var c = doc.body && doc.body.classList; return !!c && (c.contains('spb-polish-f-off') || c.contains('spb-polish-off')); }
    function isFoldable(k) {
        return k && k.tagName === 'DETAILS' && k.classList.contains('spb-tb-menu') && !k.classList.contains('spb-tb-menu-right');
    }
    function rowMenus() {
        var out = [], kids = bar.children;
        for (var i = 0; i < kids.length; i++) if (isFoldable(kids[i])) out.push(kids[i]);
        return out;
    }
    function build() {
        bar = doc.getElementById('spbTopToolbar');
        if (!bar || bar.querySelector(':scope > #spbPfMore')) return !!bar;
        wrap = doc.createElement('div'); wrap.id = 'spbPfMore'; wrap.className = 'spb-pf-more'; wrap.hidden = true;
        btn = doc.createElement('button'); btn.type = 'button'; btn.id = 'spbPfMoreBtn'; btn.className = 'spb-pf-more-btn';
        btn.setAttribute('aria-haspopup', 'true'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'spbPfMorePop');
        btn.title = 'More menus: the tool menus that do not fit at this window width'; btn.innerHTML = 'Menus <span class="spb-tb-caret" aria-hidden="true">▾</span>';
        pop = doc.createElement('div'); pop.id = 'spbPfMorePop'; pop.className = 'spb-pf-more-pop';
        wrap.appendChild(btn); wrap.appendChild(pop);
        // right after the last foldable menu (before the separator that precedes Zone | Layer)
        var list = rowMenus(), last = list.length ? list[list.length - 1] : null;
        if (last) last.parentNode.insertBefore(wrap, last.nextSibling); else bar.appendChild(wrap);
        btn.addEventListener('click', function (e) { e.stopPropagation(); if (wrap.classList.contains('open')) closeMore(); else openMore(); });
        btn.addEventListener('keydown', function (e) { if (e.key === 'ArrowDown' && !wrap.classList.contains('open')) { e.preventDefault(); openMore(); } });
        doc.addEventListener('click', function (e) { if (wrap.classList.contains('open') && !wrap.contains(e.target)) closeMore(); });
        // clicking an action inside a folded menu: the panel closes once no accordion row stays open (like a normal menu closing on a click)
        pop.addEventListener('click', function (e) {
            if (!e.target.closest || !e.target.closest('.spb-tb-pop')) return;
            setTimeout(function () { if (!pop.querySelector('details[open]')) closeMore(); }, 0);
        });
        // opening a normal menu in the row closes the panel
        bar.addEventListener('toggle', function (e) {
            var m = e.target;
            if (m && m.matches && m.matches('details.spb-tb-menu') && m.open && !pop.contains(m)) closeMore();
        }, true);
        doc.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape' || !wrap.classList.contains('open')) return;
            if (pop.querySelector('details[open]')) return;   // tool-menus.js closes the open row first
            e.preventDefault(); e.stopImmediatePropagation(); closeMore(); btn.focus({ preventScroll: true });
        }, true);
        return true;
    }
    function openMore() {
        var open = bar.querySelectorAll('details.spb-tb-menu[open]');
        for (var i = 0; i < open.length; i++) open[i].open = false;
        wrap.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
    }
    function closeMore() {
        if (!wrap) return;
        wrap.classList.remove('open'); btn.setAttribute('aria-expanded', 'false');
        var open = pop.querySelectorAll('details[open]');
        for (var i = 0; i < open.length; i++) open[i].open = false;
    }
    function unfoldAll() {
        for (var i = 0; i < folded.length; i++) bar.insertBefore(folded[i], wrap);
        folded.length = 0;
    }
    function foldOne(m) {
        m.open = false;
        pop.insertBefore(m, pop.firstChild);
        folded.unshift(m);
    }
    // true when the last visible child of the row sticks out of the bar's content box
    function overflowing() {
        var cs = getComputedStyle(bar);
        var lim = bar.getBoundingClientRect().right - (parseFloat(cs.paddingRight) || 0) - (parseFloat(cs.borderRightWidth) || 0);
        var kids = bar.children;
        for (var i = kids.length - 1; i >= 0; i--) {
            var k = kids[i];
            if (k.hidden) continue;
            var r = k.getBoundingClientRect();
            if (!r.width && !r.height) continue;
            return r.right > lim + 0.5;
        }
        return false;
    }
    function fit() {
        raf = 0;
        if (busy || !build()) return;
        var force = wantForce; wantForce = false;
        // nothing relevant changed (same bar width, same menus, same kill-switch state): leave an open panel alone
        var key = bar.clientWidth + '|' + (rowMenus().length + folded.length) + '|' + (off() ? 1 : 0);
        if (!force && key === lastKey) return;
        busy = true;
        try {
            lastKey = key;
            closeMore();
            unfoldAll();
            wrap.hidden = true;
            if (off()) return;
            if (!bar.getClientRects().length || bar.clientWidth < 200) return;   // toolbar not on screen (chat view): nothing to measure
            if (!overflowing()) return;
            wrap.hidden = false;
            var list = rowMenus();
            for (var i = list.length - 1; i >= 0 && overflowing(); i--) foldOne(list[i]);
            if (!folded.length) wrap.hidden = true;
        } finally {
            if (mo) mo.takeRecords();   // our own moves are not news
            busy = false;
        }
    }
    // 2026-10-12 (S2 UI polish, orchestrator report): a hidden / background tab never delivers requestAnimationFrame, so `raf` stayed non-zero for good and the fold never ran
    // (page overflowed to 1350 px at 1100 wide). A short timer now runs fit() when the frame did not arrive; in a visible window rAF fires first and the timer is a no-op.
    function schedule(force) {
        if (force === true) wantForce = true;
        if (raf) return;
        var mine = raf = requestAnimationFrame(fit);
        setTimeout(function () { if (raf === mine) { try { cancelAnimationFrame(mine); } catch (_) {} fit(); } }, 120);
    }
    function start() {
        if (!build()) { setTimeout(start, 400); return; }
        window.addEventListener('resize', function () { schedule(false); });
        if (window.ResizeObserver) { try { new ResizeObserver(function () { schedule(false); }).observe(bar); } catch (_) {} }
        if (window.MutationObserver) {
            try {
                mo = new MutationObserver(function () { schedule(true); });
                mo.observe(bar, { childList: true });
                new MutationObserver(function () { schedule(false); }).observe(doc.body, { attributes: true, attributeFilter: ['class'] });   // the key above notices a kill-switch flip
            } catch (_) {}
        }
        if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(function () { schedule(true); });
        window.addEventListener('load', function () { schedule(true); setTimeout(function () { schedule(true); }, 800); setTimeout(function () { schedule(true); }, 2500); });
        schedule(true);
    }
    // ---- compact tool hint ---------------------------------------------------------------------------------------------------------------------------
    // flashToolHint(title, body) (paint-booth-3-canvas.js [04]) used to pop a 550px box centred at top:11% on EVERY tool switch; at 1100px it sat on top of the
    // tool band (the History / Select / Retouch menus). Same element (#platinumToolFlash), same text source (TOOL_GUIDE), now: title + shortcut chip + the first
    // sentence only (<=118 chars), anchored under the tool button that is active, BELOW the band, after a 280 ms delay (rapid tool changes show only the last), and gone on the
    // next pointer press / Esc / menu open. Kill switch: body.spb-polish-f-off restores the old call.
    function menuIsOpen() { return !!(doc.querySelector('details.spb-tb-menu[open]') || (wrap && wrap.classList.contains('open'))); }
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function shortcutOf(body) { var m = /\[\s*([A-Za-z0-9+\-\/ ]{1,14}?)\s*\]/.exec(body || ''); return m ? m[1].replace(/\s+/g, ' ').trim() : ''; }
    function compactBody(body) {
        var t = String(body || '').replace(/\[[^\]]*\]/g, ' ').replace(/[·•]\s*/g, ' ').replace(/\s+/g, ' ').trim();
        var m = /^(.+?[.!?])(\s|$)/.exec(t); if (m) t = m[1];
        if (t.length > 118) t = t.slice(0, 118).replace(/\s+\S*$/, '') + '…';
        return t;
    }
    function anchorBtn() {
        var list = doc.querySelectorAll('#spbTopToolbar .vtool-btn.active');
        for (var i = 0; i < list.length; i++) if (list[i].offsetParent !== null) return list[i];
        return null;
    }
    function placeTip(el) {
        var tb = (bar || doc.getElementById('spbTopToolbar')); if (!tb) return;
        var tr = tb.getBoundingClientRect(), vw = doc.documentElement.clientWidth, a = anchorBtn(), ar = a ? a.getBoundingClientRect() : null;
        var w = el.offsetWidth, cx = ar ? ar.left + ar.width / 2 : 40;
        var left = Math.max(8, Math.min(vw - w - 8, cx - 22));
        el.style.setProperty('left', Math.round(left) + 'px', 'important');
        el.style.setProperty('top', Math.round(tr.bottom + 7) + 'px', 'important');
        el.style.setProperty('--pf-caret', Math.round(Math.max(10, Math.min(w - 18, cx - left - 4))) + 'px');
    }
    function hideTip() {
        var el = doc.getElementById('platinumToolFlash'); if (!el) return;
        clearTimeout(el._pfD);
        if (el.style.opacity !== '0') { clearTimeout(el._t); el.style.opacity = '0'; }
    }
    function wrapFlash() {
        var orig = window.flashToolHint;
        if (typeof orig !== 'function') return false;
        if (orig.__spbPf) return true;
        var w = function (title, body, ms) {
            if (off()) return orig.apply(this, arguments);
            var key = shortcutOf(body), html = String(title == null ? '' : title) + (key ? ' <span class="spb-pf-key">' + esc(key) + '</span>' : '');
            var r = orig.call(this, html, body ? compactBody(body) : '', ms);
            var el = doc.getElementById('platinumToolFlash');
            if (!el) return r;
            clearTimeout(el._t); clearTimeout(el._pfD); el.style.opacity = '0';
            el._pfD = setTimeout(function () {
                if (off() || menuIsOpen()) return;
                placeTip(el); el.style.opacity = '1';
                clearTimeout(el._t); el._t = setTimeout(function () { el.style.opacity = '0'; }, ms || (body ? 3200 : 1100));
            }, 280);
            return r;
        };
        w.__spbPf = true; w.__orig = orig; window.flashToolHint = w;
        return true;
    }
    function startTip() {
        var tries = 0;
        (function tryWrap() { if (!wrapFlash() && ++tries < 40) setTimeout(tryWrap, 250); })();
        doc.addEventListener('pointerdown', hideTip, true);
        doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideTip(); }, true);
        doc.addEventListener('toggle', function (e) { var d = e.target; if (d && d.classList && d.classList.contains('spb-tb-menu') && d.open) hideTip(); }, true);
    }
    // ---- narrow canvas column flag --------------------------------------------------------------------------------------------------------------------
    // The 1100px window leaves the canvas column ~392px wide (two ~183px panes). Below 520px the Refresh pill and the tool options row use the compact layout in the F CSS block.
    function startNarrow() {
        var tries = 0;
        (function tryIt() {
            var c = doc.getElementById('splitViewContainer');
            if (!c) { if (++tries < 40) setTimeout(tryIt, 500); return; }
            function upd() { var w = c.clientWidth; c.classList.toggle('spb-pf-narrow', w > 0 && w < 520); }
            upd();
            if (window.ResizeObserver) { try { new ResizeObserver(upd).observe(c); } catch (_) {} }
            window.addEventListener('resize', upd);
        })();
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { start(); startTip(); startNarrow(); }); else { start(); startTip(); startNarrow(); }
})();
