/* [SPB-TICKETS-FIX 2026-10-10] small fixes for the INTEGRATION-QA tickets whose owning lanes had finished.
 *   T-5   the destructive "Adjust > Hue / Saturation" (and its three twins) is now named for what it does ("changes pixels") so it cannot be
 *         mistaken for "Layer Actions > + Adjustment layer > Hue/Saturation" (own layer + mask, non-destructive).
 *   R-1   (coordinator item 1) the Render Recipe result card can never stay on "Building recipe card..." forever: if drawing it throws (or the
 *         image loads hang) the plain zone table is shown after 25 s / at once.
 *   T-7   the bottom option bar (#toolOptionsBar) fits at any width: what does not fit goes behind a "..." popover, the bar keeps its fixed height
 *         and nothing moves on a tool switch (added in the T-7 block below).
 * Kill switch: window.SPB_TFIX_OFF = true (before load) or localStorage SPB_TFIX_OFF = '1'; each block also has window.SPB_TFIX_<id>_OFF.
 * Every function is wrapped so a failure here can never break the page. */
(function (root) {
    'use strict';
    var doc = root && root.document; if (!doc) return;
    function off(id) {
        if (root.SPB_TFIX_OFF || (id && root['SPB_TFIX_' + id + '_OFF'])) return true;
        try { if (root.localStorage.getItem('SPB_TFIX_OFF') === '1') return true; } catch (e) {}
        return false;
    }
    if (off()) return;
    function safe(fn) { return function () { try { return fn.apply(this, arguments); } catch (e) { try { console.warn('[SPB-TICKETS-FIX]', e && e.message || e); } catch (_) {} } }; }

    // ------------------------------------------------------------------ style (own block, removed with the kill switch because nothing loads)
    var st = doc.createElement('style'); st.id = 'spbTfixStyle'; st.setAttribute('data-spb-tfix', '1');
    st.textContent = [
        '.spb-tf-sub{margin-left:6px;font-size:9px;font-weight:400;opacity:.62;white-space:nowrap}',
        '.spb-tf-note{padding:14px 16px;font-size:12px;color:var(--pl-tx2,#9aa4b2)}',
        // T-7: the "..." button and its popover (everything is !important because the option bars sit under a stack of !important rail rules)
        '.spb-tf-more{flex:0 0 auto !important;order:99 !important;margin:0 0 0 auto !important;align-self:center !important;height:22px !important;min-width:30px !important;padding:0 8px !important;box-sizing:border-box !important;border:1px solid var(--pl-bd,#3a3a42) !important;border-radius:6px !important;background:var(--pl-app,#1c1c1f) !important;color:var(--pl-tx,#e6e6ea) !important;font:700 14px/1 inherit !important;letter-spacing:1px !important;cursor:pointer !important;display:inline-flex;align-items:center;justify-content:center}',
        '.spb-tf-more:hover,.spb-tf-more[aria-expanded="true"]{background:var(--pl-hov,#2a2a30) !important;border-color:var(--pl-ac,#22d3ee) !important}',
        '.spb-tf-more:focus-visible{outline:2px solid var(--pl-ac,#22d3ee);outline-offset:1px}',
        '.spb-tf-pop{position:fixed;z-index:9500;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 12px;max-height:60vh;overflow:auto;box-sizing:border-box;background:var(--pl-panel,#202024);border:1px solid var(--pl-bd,#3a3a42);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.5)}',
        '.spb-tf-pop[hidden],.spb-tf-more[hidden]{display:none !important}',
        '.spb-tf-hid{display:none !important}',
        'body #toolOptionsBar .spb-tf-hid.spb-tf-hid,body.spb-toolrow-on #spbToolRowTop>.spb-tf-hid.spb-tf-hid{display:none !important}',
        '.spb-tf-u{display:inline-flex;align-items:center;gap:6px;white-space:nowrap}',
        '.spb-tf-u>*{flex:0 0 auto}',
        'body.spb-toolrow-on #spbToolRowTop.spb-tf-tight{gap:4px 4px !important;padding-left:6px !important;padding-right:6px !important}',
        'body.spb-toolrow-on #spbToolRowTop.spb-tf-tight .spb-tr-group{gap:3px !important}'
    ].join('\n');
    (doc.head || doc.documentElement).appendChild(st);

    // ------------------------------------------------------------------ T-5 names
    // [SPB-TICKETS-FIX 2026-10-10 T-5]
    var DESTRUCTIVE = [
        ['promptAdjustHueSat', 'Hue / Saturation', 'Hue/Saturation'],
        ['promptAdjustBrightnessContrast', 'Brightness / Contrast', 'Brightness/Contrast'],
        ['promptInvertColors', 'Invert Colors', 'Invert'],
        ['promptVibrance', 'Vibrance', 'Vibrance']
    ];
    var markNames = safe(function () {
        if (off('T5')) return;
        DESTRUCTIVE.forEach(function (d) {
            var b = doc.querySelector('.spb-tb-pop button[onclick*="' + d[0] + '("]');
            if (!b || b.getAttribute('data-tf-t5')) return;
            b.setAttribute('data-tf-t5', '1');
            var sub = doc.createElement('span'); sub.className = 'spb-tf-sub'; sub.textContent = '(changes pixels)';
            b.appendChild(sub);
            var t = b.getAttribute('title') || '';
            b.setAttribute('title', t + (t ? '. ' : '') + 'Changes the selected layer\'s pixels for good (undo restores them). For a version you can mask and switch off, use Layer Actions > + Adjustment layer > ' + d[2] + '.');
        });
    });

    // ------------------------------------------------------------------ R-1 Render Recipe card never stuck
    // [SPB-TICKETS-FIX 2026-10-10 R-1] renderRecipeCardUI() builds the model BEFORE its try/catch and waits on four image loads; a throw or a hang left the
    // result overlay on "Building recipe card..." for good. The wrapper adds a 25 s watchdog and a catch that falls back to the plain zone table.
    // Two more latent defects in the page's own fallback, found while proving this: (1) css `.spb-render-modal #renderRecipeZones{display:none !important}`
    // keeps the zone table hidden even when the code "shows" it, so the fallback was a blank panel; (2) the table is MOVED into the stage, and the next
    // normal render does `stage.innerHTML=''`, which deleted the table from the page for good. -> show it with an inline !important and move it
    // back to its home before every render.
    var tblHome = null;
    function recipeTable() { return doc.getElementById('renderRecipeZones'); }
    function rememberHome() {
        var t = recipeTable();
        if (t && !tblHome && t.parentNode && t.parentNode.id !== 'recipeCardStage') tblHome = { p: t.parentNode, n: t.nextSibling };
    }
    function restoreHome() {
        var t = recipeTable();
        if (!t || !tblHome || !t.parentNode || t.parentNode.id !== 'recipeCardStage') return;
        t.style.removeProperty('display'); t.style.removeProperty('width');
        tblHome.p.insertBefore(t, (tblHome.n && tblHome.n.parentNode === tblHome.p) ? tblHome.n : null);
    }
    function showTable(t) { if (t) { t.style.setProperty('display', 'flex', 'important'); t.style.width = '100%'; } }
    function recipeFallback(why) {
        var stage = doc.getElementById('recipeCardStage'); if (!stage) return;
        if (!stage.querySelector('.recipe-card-loading') && !(recipeTable() && recipeTable().parentNode === stage)) return;   // card drawn or replaced: leave it
        rememberHome();
        var tbl = recipeTable();
        stage.innerHTML = '<div class="spb-tf-note">The recipe card could not be drawn' + (why ? ' (' + why + ')' : '') + '. Your render is saved; the zone table is below.</div>';
        if (tbl) { stage.style.flexDirection = 'column'; stage.appendChild(tbl); showTable(tbl); }
        try { if (typeof root.buildRenderRecipeZones === 'function') root.buildRenderRecipeZones(); } catch (e) {}
    }
    var wrapRecipe = safe(function () {
        var orig = root.renderRecipeCardUI;
        if (typeof orig !== 'function' || orig.__tfR1) return typeof orig === 'function';
        rememberHome();
        var w = function () {
            if (off('R1')) return orig.apply(this, arguments);
            restoreHome();
            var st = doc.getElementById('recipeCardStage'); if (st) st.style.flexDirection = '';
            var wd = setTimeout(function () { recipeFallback('it took too long'); }, 25000), p;
            var fixShown = function () {   // the page's own catch-fallback shows the table too: make it visible there as well
                var s = doc.getElementById('recipeCardStage'), t = recipeTable();
                if (s && t && t.parentNode === s) { s.style.flexDirection = 'column'; showTable(t); }
            };
            try { p = orig.apply(this, arguments); } catch (e) { clearTimeout(wd); recipeFallback(e && e.message); return; }
            return Promise.resolve(p).then(function (v) { clearTimeout(wd); safe(fixShown)(); return v; }, function (e) { clearTimeout(wd); recipeFallback(e && e.message); });
        };
        w.__tfR1 = true; root.renderRecipeCardUI = w; return true;
    });

    // ------------------------------------------------------------------ T-7 option bars never scroll sideways or cut a control in half
    // [SPB-TICKETS-FIX 2026-10-10 T-7] The bottom bar (#toolOptionsBar) and the tool band (#spbToolRowTop) were single fixed-height rows that scrolled
    // sideways (Brush 1839 px of options in a 644 px bar, Text 1216, Eyedropper 975; band 735 in 644), so "Fl..." was cut off and the rest was a scrollbar hunt.
    // Priority+ overflow: every control that does not fit WHOLE is hidden in place (class .spb-tf-hid, never a half control) and a "..." button at the
    // end of the row opens a popover with exactly those controls (the real nodes, moved while it is open and put back on close, so ids, listeners and
    // the app's own getElementById calls keep working). The row height never changes, so nothing moves when you switch tool. The band first tries a
    // tighter gap/padding before it uses the button. Hiding goes on the CONTAINER when all of its controls are hidden, because the app's
    // _railHasVisibleToolOptions() reads each control's own computed display (a collapsed rail would take the "..." button with it).
    function isShown(el) {
        if (!el || el.nodeType !== 1 || el.classList.contains('spb-tf-more') || el.classList.contains('spb-tf-pop')) return false;
        var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
    }
    function groupKids(c) {          // label + slider + value stay one unit; every other control is its own unit
        var units = [], cur = null;
        Array.prototype.forEach.call(c.children, function (k) {
            if (!isShown(k)) return;
            var tg = k.tagName;
            if (tg === 'LABEL') { cur = [k]; units.push(cur); return; }
            if (cur && (tg === 'INPUT' || (tg === 'SPAN' && !k.children.length && (k.textContent || '').length <= 8 && cur.length >= 2) || (tg === 'SELECT' && cur.length === 1))) { cur.push(k); return; }
            cur = null; units.push([k]);
        });
        return units;
    }
    function barUnits(bar) {
        var us = [];
        Array.prototype.forEach.call(bar.children, function (c) {
            if (!isShown(c)) return;
            if (c.id === 'toolSpecificOptions' || c.id === 'contextActionsBar') groupKids(c).forEach(function (u) { us.push(u); });
            else us.push([c]);
        });
        us.sort(function (a, b) { return a[0].getBoundingClientRect().left - b[0].getBoundingClientRect().left; });
        return us;
    }
    function bandUnits(row) {
        var us = [];
        Array.prototype.forEach.call(row.children, function (c) { if (isShown(c)) us.push([c]); });
        return us;
    }
    // Hide = class first (a stylesheet !important beats the inline display tool-options-split.js keeps writing on the band groups, and it writes NOTHING
    // inline, so the two observers cannot ping-pong). Only where an even stronger rule keeps the element displayed (the rail css forces display:flex
    // !important on #toolSpecificOptions / #contextActionsBar) fall back to an inline !important, remembering the app's own inline display and giving it
    // back untouched unless the app changed it meanwhile.
    function hideEl(e) {
        e.classList.add('spb-tf-hid');
        if (root.getComputedStyle(e).display !== 'none') {
            if (!e.__tfd) e.__tfd = { v: e.style.getPropertyValue('display'), p: e.style.getPropertyPriority('display') };
            e.style.setProperty('display', 'none', 'important');
        }
    }
    function unhideEl(e) {
        e.classList.remove('spb-tf-hid');
        if (!e.__tfd) return;
        var d = e.__tfd; e.__tfd = null;
        if (e.style.getPropertyValue('display') === 'none' && e.style.getPropertyPriority('display') === 'important') {
            if (d.v) e.style.setProperty('display', d.v, d.p); else e.style.removeProperty('display');
        }
    }
    function unitRight(u) { var m = -1e9; u.forEach(function (e) { var r = e.getBoundingClientRect().right; if (r > m) m = r; }); return m; }
    function lastRight(us) { var m = -1e9; us.forEach(function (u) { var r = unitRight(u); if (r > m) m = r; }); return m; }

    function makeFit(id, pos, units, tight) {
        var F = { id: id, pos: pos, units: units, tight: tight, more: null, pop: null, mo: null, ro: null, busy: false, drag: false, isOpen: false, moved: [], hiddenUnits: [], root: function () { return doc.getElementById(id); } };
        function flush() { try { if (F.mo) F.mo.takeRecords(); } catch (e) {} }
        function ensureUi(rt) {
            if (!F.more || F.more.parentNode !== rt) {
                if (F.more && F.more.parentNode) F.more.parentNode.removeChild(F.more);
                var b = doc.createElement('button'); b.type = 'button'; b.className = 'spb-tf-more'; b.hidden = true; b.textContent = '⋯';
                b.setAttribute('aria-haspopup', 'true'); b.setAttribute('aria-expanded', 'false'); b.setAttribute('data-spb-tf', 'more');
                b.title = 'More options'; b.setAttribute('aria-label', 'More options');
                b.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); if (F.isOpen) { F.close(); F.run(); } else F.open(); });
                rt.appendChild(b); F.more = b;
            }
            if (!F.pop || F.pop.parentNode !== rt) {
                if (F.pop && F.pop.parentNode) F.pop.parentNode.removeChild(F.pop);
                var p = doc.createElement('div'); p.className = 'spb-tf-pop'; p.hidden = true; p.setAttribute('role', 'group'); p.setAttribute('aria-label', 'More options');
                rt.appendChild(p); F.pop = p;
            }
            if (!rt.__spbTf7) {
                rt.__spbTf7 = true;
                rt.style.setProperty('overflow-x', 'hidden', 'important'); rt.style.setProperty('scrollbar-gutter', 'auto', 'important');
                rt.addEventListener('pointerdown', function (ev) { if (ev.target && ev.target.closest && ev.target.closest('input[type="range"]') && !ev.target.closest('.spb-tf-pop')) F.drag = true; }, true);
                try {
                    F.mo = new root.MutationObserver(function (recs) {
                        var rel = recs.some(function (r) {
                            var t = r.target;
                            if (t === F.more || (F.pop && (t === F.pop || F.pop.contains(t)))) return false;
                            if (t === rt && r.type === 'attributes') return false;
                            if (F.isOpen && r.type === 'attributes') return false;   // slider-fill / hover styling is noise while the popover is open
                            return true;
                        });
                        if (rel) F.run();
                    });
                    F.mo.observe(rt, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
                } catch (e) {}
                try { if (root.ResizeObserver) { F.ro = new root.ResizeObserver(function () { F.run(); }); F.ro.observe(rt); } } catch (e) {}
            }
        }
        F.close = function () {
            if (!F.isOpen) return;
            F.isOpen = false;
            F.moved.forEach(function (x) {
                if (x.m.parentNode) { x.m.parentNode.insertBefore(x.el, x.m); x.m.parentNode.removeChild(x.m); }
                else if (x.el.parentNode) x.el.parentNode.removeChild(x.el);          // the app re-rendered its row: this copy is stale
            });
            F.moved = [];
            if (F.pop) { F.pop.innerHTML = ''; F.pop.hidden = true; }
            if (F.more) F.more.setAttribute('aria-expanded', 'false');
            flush();
        };
        F.open = function () {
            var rt = F.root(); if (!rt || F.isOpen || !F.hiddenUnits.length || !F.pop) return;
            F.moved = [];
            F.hiddenUnits.forEach(function (u) {
                var w = doc.createElement('span'); w.className = 'spb-tf-u';
                u.forEach(function (el) {
                    if (!el.parentNode) return;
                    var m = doc.createComment('spb-tf'); el.parentNode.insertBefore(m, el); w.appendChild(el);
                    unhideEl(el); F.moved.push({ el: el, m: m });
                });
                F.pop.appendChild(w);
            });
            F.pop.hidden = false; F.isOpen = true; F.more.setAttribute('aria-expanded', 'true');
            var br = F.more.getBoundingClientRect(), rr = rt.getBoundingClientRect(), vw = root.innerWidth, vh = root.innerHeight;
            F.pop.style.maxWidth = Math.max(240, Math.min(640, vw - 24)) + 'px';
            var w2 = F.pop.offsetWidth, h2 = F.pop.offsetHeight;
            var left = Math.max(8, Math.min(br.right - w2, vw - w2 - 8));
            var top = F.pos === 'up' ? rr.top - h2 - 6 : rr.bottom + 6;
            top = Math.max(8, Math.min(top, vh - h2 - 8));
            F.pop.style.left = left + 'px'; F.pop.style.top = top + 'px';
            flush();
        };
        F.undo = function () {      // back to the old behaviour (a sideways-scrolling row): used by the circuit breaker
            var rt = F.root(); F.close();
            if (rt) { Array.prototype.forEach.call(rt.querySelectorAll('.spb-tf-hid'), unhideEl); rt.classList.remove('spb-tf-tight'); rt.style.removeProperty('overflow-x'); rt.style.removeProperty('scrollbar-gutter'); }
            if (F.more) F.more.hidden = true;
            flush();
        };
        F.run = function () {
            if (F.busy || F.drag || F.dead || off('T7')) return;
            var now = Date.now(); if (now < (F.pausedUntil || 0)) return;
            // circuit breaker: if another script answers every change we make (a ping-pong), never spin the page: pause, and give up for good after 3 trips
            F.runs = (F.runs || []).filter(function (t) { return now - t < 1000; }); F.runs.push(now);
            if (F.runs.length > 40) {
                F.trips = (F.trips || 0) + 1; F.pausedUntil = now + 5000; if (F.trips >= 3) F.dead = true;
                try { console.warn('[SPB-TICKETS-FIX T-7] ' + id + ' fit paused (changes answered too fast); trip ' + F.trips); } catch (e) {}
                F.undo(); return;
            }
            var rt = F.root(); if (!rt || !rt.isConnected) return;
            F.busy = true;
            var reopen = F.isOpen;
            try {
                if (F.isOpen) F.close();
                ensureUi(rt);
                rt.scrollLeft = 0;
                Array.prototype.forEach.call(rt.querySelectorAll('.spb-tf-hid'), unhideEl);
                F.more.hidden = true; rt.classList.remove('spb-tf-tight'); F.hiddenUnits = [];
                var rr = rt.getBoundingClientRect(); if (rr.width < 60) return;
                var cs = root.getComputedStyle(rt), limit = rr.right - (parseFloat(cs.paddingRight) || 0);
                var us = F.units(rt), right = lastRight(us);
                if (!us.length) return;
                if (right > limit + 0.5 && F.tight) { rt.classList.add('spb-tf-tight'); us = F.units(rt); right = lastRight(us); }
                if (right > limit + 0.5) {
                    F.more.hidden = false;
                    var gap = parseFloat(root.getComputedStyle(rt).columnGap) || 8, lim2 = limit - F.more.getBoundingClientRect().width - gap, keep = 0;
                    for (var i = 0; i < us.length; i++) { if (unitRight(us[i]) <= lim2 + 0.5) keep = i + 1; else break; }
                    var hid = us.slice(keep), set = [];
                    hid.forEach(function (u) { u.forEach(function (e) { set.push(e); }); });
                    var parents = [];
                    set.forEach(function (e) { var p = e.parentNode; if (p && p !== rt && parents.indexOf(p) < 0) parents.push(p); });
                    var wholeParent = [];
                    parents.forEach(function (p) {
                        var all = true;
                        Array.prototype.forEach.call(p.children, function (ch) { if (set.indexOf(ch) >= 0) return; if (ch === F.more || ch === F.pop) return; if (root.getComputedStyle(ch).display === 'none') return; all = false; });
                        if (all) { wholeParent.push(p); hideEl(p); }
                    });
                    set.forEach(function (e) { if (wholeParent.indexOf(e.parentNode) < 0) hideEl(e); });
                    F.hiddenUnits = hid;
                    F.more.title = 'More options (' + hid.length + ')';
                }
            } finally { F.busy = false; flush(); }
            if (reopen && F.hiddenUnits.length) F.open();     // the app re-rendered its row under an open popover: rebuild it from the fresh controls
        };
        return F;
    }

    var t7 = { bar: null, band: null };
    var t7Boot = safe(function () {
        if (off('T7')) return;
        if (!t7.bar && doc.getElementById('toolOptionsBar')) { t7.bar = makeFit('toolOptionsBar', 'up', barUnits, false); t7.bar.run(); }
        if (!t7.band && doc.getElementById('spbToolRowTop')) { t7.band = makeFit('spbToolRowTop', 'down', bandUnits, true); t7.band.run(); }
    });
    if (!off('T7')) {
        doc.addEventListener('pointerdown', function (ev) {
            [t7.bar, t7.band].forEach(function (F) {
                if (!F || !F.isOpen) return;
                if ((F.pop && F.pop.contains(ev.target)) || (F.more && F.more.contains(ev.target))) return;
                F.close(); F.run();
            });
        }, true);
        doc.addEventListener('pointerup', function () { [t7.bar, t7.band].forEach(function (F) { if (F && F.drag) { F.drag = false; F.run(); } }); }, true);
        doc.addEventListener('pointercancel', function () { [t7.bar, t7.band].forEach(function (F) { if (F && F.drag) { F.drag = false; F.run(); } }); }, true);
        doc.addEventListener('keydown', function (ev) {
            if (ev.key !== 'Escape') return;
            [t7.bar, t7.band].forEach(function (F) { if (F && F.isOpen) { var m = F.more; F.close(); F.run(); try { m.focus(); } catch (e) {} } });
        }, true);
        root.addEventListener('resize', function () { [t7.bar, t7.band].forEach(function (F) { if (F) F.run(); }); });
    }

    // ------------------------------------------------------------------ boot
    var tries = 0;
    var t = setInterval(function () {
        tries++;
        markNames(); var r = wrapRecipe(); t7Boot();
        if (tries > 40 && r) clearInterval(t);
        if (tries > 120) clearInterval(t);
    }, 500);
    setInterval(markNames, 4000);     // the toolbar menus can be rebuilt; keep the names
    setInterval(safe(function () { if (doc.hidden) return; [t7.bar, t7.band].forEach(function (F) { if (F && !F.isOpen) F.run(); }); }), 2500);   // safety net: value labels grow, fonts load
    root.SPBTicketsFix = { version: '2026-10-10', off: off, markNames: markNames, recipeFallback: recipeFallback, t7: t7 };
})(typeof window !== 'undefined' ? window : null);
