/* [SPB-POLISH-H 2026-10-10] tonight's tools feel like ONE product. Owner: "MAKING the UI/UX look like a REAL PRODUCT and not as vibecoded".
   Audit (before): _easy_claude_work/ui_polish/polish_h/AUDIT.md - kits opened at the window's top-left corner at 1100 px (anchored to a folded
   menu) and over the canvas at 1920; panels piled up on 4 z layers; "Symmetry" held the Number / Sponsor kits.
   This file (no tool logic touched; every tool opens and applies through its own code):
   1. MENUS  - "Symmetry" -> "Car" (Mirror | Place On The Car | Across The Car), "Material" -> "Material / Spec" (Brushes | Whole Car).
              Items are only re-ordered INSIDE their own menu (each menu delegates its clicks, POLISH-F folding moves whole menus), group
              labels are inert, and entries that live elsewhere (Layer Materials, Shine Lens, a Race Wear entry in another menu) get a proxy
              item that clicks the real control. (Pro has no installed command palette - Ctrl+K does nothing today - so there is
              nothing to add keywords to; js/zones/catalog-workflow-controls.js is never installed.)
   2. DOCK   - a panel opens in the free gutter beside the canvases (1920: over the zone editor, left of the Source); with no gutter (1100)
              at the left edge (Source side), never over the Live Preview. Top = under the tool band, max-height = window. Dragging the
              header moves it (own drag for the two panels that had none) and the panel then stays where the painter put it (remembered,
              double-click the header to dock it again). Newest panel on top.
   3. SHELL  - css/spb-polish-h-20261010.css (loaded last).
   Kill switch: body.spb-polish-h-off or window.SPB_POLISH_H_OFF = true (menus go back to the old names + order, no docking). */
(function () {
    'use strict';
    if (window.__spbPolishH) return;
    var doc = document, root = window;
    var VERSION = '20261010-t4a';
    function off() { var b = doc.body; return !!root.SPB_POLISH_H_OFF || !!(b && b.classList.contains('spb-polish-h-off')); }
    function toast(m) { try { if (typeof root.showToast === 'function') root.showToast(m, 'info'); } catch (_) {} }
    function txt(e) { return (e && e.textContent || '').replace(/\s+/g, ' ').trim(); }

    // ------------------------------------------------------------------------------------------------ 1. menus
    var GRP = 'spb-ph-grp', PROXY = 'spb-ph-proxy';
    var saved = {};   // menu id -> { label, title, order: [nodes] }
    function grp(label) { var d = doc.createElement('div'); d.className = GRP; d.setAttribute('role', 'presentation'); d.setAttribute('aria-hidden', 'true'); d.textContent = label; return d; }
    function proxy(key, label, title, fn) {
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'vtool-btn ' + PROXY; b.setAttribute('data-ph', key); b.title = title;
        b.innerHTML = '<span class="spb-mi-ico"></span> ' + label;
        b.addEventListener('click', function (e) { e.preventDefault(); var d = b.closest('details'); if (d) d.removeAttribute('open'); fn(b); });
        return b;
    }
    function setSummary(menu, label, title) {
        var s = menu && menu.querySelector(':scope > summary'); if (!s) return;
        var tn = null; for (var i = 0; i < s.childNodes.length; i++) if (s.childNodes[i].nodeType === 3 && s.childNodes[i].nodeValue.trim()) { tn = s.childNodes[i]; break; }
        if (!saved[menu.id]) saved[menu.id] = { label: tn ? tn.nodeValue : '', title: s.getAttribute('title') || '' };
        if (tn && tn.nodeValue.trim() !== label) tn.nodeValue = label + ' ';
        if (title && s.getAttribute('title') !== title) s.setAttribute('title', title);
    }
    function restoreMenu(menu) {
        var sv = menu && saved[menu.id]; if (!sv) return;
        var s = menu.querySelector(':scope > summary');
        if (s) { for (var i = 0; i < s.childNodes.length; i++) if (s.childNodes[i].nodeType === 3 && s.childNodes[i].nodeValue.trim()) { s.childNodes[i].nodeValue = sv.label; break; } if (sv.title) s.setAttribute('title', sv.title); }
        var pop = menu.querySelector('.spb-tb-pop');
        if (pop && sv.order) {
            var kids = Array.prototype.slice.call(pop.children).filter(function (n) { return !n.classList.contains(GRP) && !n.classList.contains(PROXY); });
            var note = pop.querySelector(':scope > .spb-sym-note');
            var want = sv.order.filter(function (n) { return n.parentNode === pop && n !== note; })
                .concat(kids.filter(function (n) { return sv.order.indexOf(n) < 0 && n !== note; }));
            if (note) want.push(note);
            // only move nodes when the order is off: every append is a toolbar mutation that would schedule this again
            if (!(want.length === kids.length && want.every(function (n, i) { return kids[i] === n; }))) want.forEach(function (n) { pop.appendChild(n); });
        }
        pop && pop.querySelectorAll('.spb-ph-hidden-orig').forEach(function (n) { n.classList.remove('spb-ph-hidden-orig'); });
        // kill switch: take our group labels + proxies out of the menu (the app's own `.spb-tb-pop .vtool-btn` display rule outranks a CSS hide);
        // they stay cached in grpCache / prox and arrange() puts them back when the switch is off again
        pop && pop.querySelectorAll(':scope > .' + GRP + ', :scope > .' + PROXY).forEach(function (n) { n.remove(); });
    }
    var cwText = null;   // the Colourway Studio label text node we re-punctuated (restored by the kill switch)
    // put `want` (array of nodes / labels / nulls) at the top of pop, in order; anything else stays after, in its old order; .spb-sym-note last
    function arrange(menu, want) {
        var pop = menu.querySelector('.spb-tb-pop'); if (!pop) return;
        var sv = saved[menu.id] || (saved[menu.id] = {});
        if (!sv.order) sv.order = Array.prototype.slice.call(pop.children).filter(function (n) { return !n.classList.contains(GRP) && !n.classList.contains(PROXY); });
        var list = want.filter(Boolean), rest = Array.prototype.slice.call(pop.children).filter(function (n) { return list.indexOf(n) < 0 && !n.classList.contains(GRP); });
        var note = pop.querySelector('.spb-sym-note');
        var seq = list.concat(rest.filter(function (n) { return n !== note; })); if (note) seq.push(note);
        var same = seq.length === pop.children.length && seq.every(function (n, i) { return pop.children[i] === n; });
        if (same) return;
        Array.prototype.slice.call(pop.querySelectorAll(':scope > .' + GRP)).forEach(function (g) { if (list.indexOf(g) < 0) g.remove(); });
        seq.forEach(function (n) { pop.appendChild(n); });
    }
    var grpCache = {};
    function G(key, label) { return grpCache[key] || (grpCache[key] = grp(label)); }
    var prox = {};
    function P(key, label, title, fn) { return prox[key] || (prox[key] = proxy(key, label, title, fn)); }
    function find(pop, re) { if (!pop) return null; var b = pop.querySelectorAll(':scope > button'); for (var i = 0; i < b.length; i++) if (!b[i].classList.contains(PROXY) && re.test(txt(b[i]))) return b[i]; return null; }
    function findAnyMenu(re, notIn) {
        var b = doc.querySelectorAll('#spbTopToolbar details .spb-tb-pop > button');
        for (var i = 0; i < b.length; i++) if (!b[i].classList.contains(PROXY) && re.test(txt(b[i])) && (!notIn || !notIn.contains(b[i]))) return b[i];
        return null;
    }

    var RE_WEAR = /race wear|wear studio/i;
    function openLayerMaterial() {
        var b = Array.prototype.slice.call(doc.querySelectorAll('.spb-lm-open')).filter(function (x) { return x.offsetParent; })[0];
        if (b) { b.click(); return; }
        toast('Layer Materials: select a layer in the Layers panel, then pick its material here.');
    }
    function toggleShine() {
        var bar = doc.getElementById('spbShineBar');
        if (!bar || !bar.offsetParent) { toast('Shine Lens lives on the Live Preview: switch to Split or Preview to use it.'); return; }
        var L = root.SPBRevLens, mode = L && L.getMode ? L.getMode() : 'off';
        var b = bar.querySelector('button[data-m="' + (mode === 'off' ? 'full' : 'off') + '"]'); if (b) b.click();
    }
    function syncMenus() {
        var car = doc.getElementById('spbSymMenu'), mat = doc.getElementById('spbRevMatMenu');
        if (off()) { restoreMenu(car); restoreMenu(mat); if (cwText && cwText.nodeValue.indexOf('…') >= 0) cwText.nodeValue = cwText.nodeValue.replace('…', '...'); return; }
        if (car) {
            setSummary(car, 'Car', 'Car: tools that know the car’s shape — mirror paint to the other side, numbers, sponsors, a centre stripe, fades across the whole car');
            var cp = car.querySelector('.spb-tb-pop');
            if (cp) {
                var wear = find(cp, RE_WEAR), wearElsewhere = wear ? null : findAnyMenu(RE_WEAR, car);
                if (wearElsewhere) wearElsewhere.classList.add('spb-ph-hidden-orig');
                arrange(car, [
                    G('mirror', 'Mirror'), cp.querySelector('[data-sym="paint"]'), cp.querySelector('[data-sym="copy"]'), cp.querySelector('[data-sym="readable"]'), cp.querySelector('[data-sym="reread"]'),
                    G('place', 'Place On The Car'), cp.querySelector('[data-nkit]') || find(cp, /Number Kit/), find(cp, /Sponsor Kit/), cp.querySelector('[data-league]') /* [SPB-REV-LEAGUE 2026-10-10 follow-up] League Pack sits with the other place-on-the-car kits */, cp.querySelector('[data-sym="stripe"]'),
                    G('across', 'Across The Car'), doc.getElementById('spbFadeMenuBtn') && cp.contains(doc.getElementById('spbFadeMenuBtn')) ? doc.getElementById('spbFadeMenuBtn') : find(cp, /Car-Space Fade/),
                    wear || (wearElsewhere ? P('wear', txt(wearElsewhere).replace(/^\W+/, ''), wearElsewhere.title || 'Race Wear', function () { wearElsewhere.click(); }) : null)
                ]);
            }
        }
        if (mat) {
            setSummary(mat, 'Material / Spec', 'Material / Spec: brush real finishes (paint + spec), give a layer its material, let Auto Spec propose a spec, check it with the Spec Doctor');
            var mp = mat.querySelector('.spb-tb-pop');
            if (mp) {
                var brushes = Array.prototype.slice.call(mp.querySelectorAll(':scope > button')).filter(function (b) { return !b.classList.contains(PROXY) && /Brush|Eyedropper|Clear Material/i.test(txt(b)) && !/Doctor|Auto Spec/i.test(txt(b)); });
                // [SHINE-OFF 2026-10-12 owner: "REMOVE the SHINE LENS from the Material/Spec dropdown"] proxy entry
                // dropped (the Shine Lens UI itself was removed 2026-10-11; this menu proxy survived). Do not re-add.
                arrange(mat, [G('brushes', 'Brushes')].concat(brushes, [
                    G('whole', 'Whole Car'),
                    P('layermat', 'Layer Materials…', 'Layer Materials: give the selected layer its own material (vinyl, chrome foil, carbon, any SPB finish); its spec follows the layer. Also in the Layers panel.', openLayerMaterial),
                    find(mp, /Auto Spec/), find(mp, /Spec Doctor/)
                ]));
            }
        }
        // Adjust > "Colourway Studio..." -> "Colourway Studio…" (one ellipsis style)
        var cw = findAnyMenu(/Colourway Studio\.\.\./);
        if (cw) { for (var i = 0; i < cw.childNodes.length; i++) { var n = cw.childNodes[i]; if (n.nodeType === 3 && /\.\.\./.test(n.nodeValue)) { n.nodeValue = n.nodeValue.replace('...', '…'); cwText = n; } } }
    }

    // ------------------------------------------------------------------------------------------------ 2. dock + drag + front
    var PANELS = {   // id -> { drag: header selector we wire ourselves (panel has no drag of its own), handle: its own drag handle }
        spbSymStripe: { drag: '.spb-sym-ph' }, spbFadePanel: { handle: '.spb-fd-ph' }, spbNumKit: { handle: '.spb-nk-ph' }, spbSponsorKit: { handle: '.spb-sk-ph' },
        spbDoctorPanel: { handle: '.spb-doc-head' }, spbAutoSpecPanel: { drag: '.spb-as-head' }, spbMatSelDlg: { handle: '#spbMtTitle' },
        spbProAI: { handle: '.spb-pai-head' }   // [TICKETS-3 item 1] the AI helper docks like the rest (its own drag stays; the shell remembers where the painter put it)
    };
    var LSK = 'spb.ph.moved';
    var moved = (function () { try { return JSON.parse(localStorage.getItem(LSK) || '{}') || {}; } catch (_) { return {}; } })();
    function saveMoved() { try { localStorage.setItem(LSK, JSON.stringify(moved)); } catch (_) {} }
    var state = {};   // id -> { el, vis, obs, x, y }
    function visible(el) { if (!el || !el.isConnected) return false; var cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && el.getClientRects().length > 0; }
    function rect(sel) { var e = doc.querySelector(sel); if (!e || !e.getClientRects().length) return null; var r = e.getBoundingClientRect(); return r.width > 20 && r.height > 20 ? r : null; }
    /* [POLISH-I 2026-10-10 item 1] kill switch window.SPB_POLISH_I_OFF (or window.SPB_POLISH_I_1_OFF for this item only).
       LEFTOVERS-3 found the dock (x = 6 when there is no gutter, top = just under the tool band) lands tool panels OVER the RENDER button
       at 1100x800 (RENDER 213..363 x 123..159; Stripe / Fade / Numbers / Sponsor / Wear / Doctor / Auto Spec / Material select all
       covered it, 4386-5100 px^2, and RENDER's centre hit-tested to the panel; Numbers + Auto Spec also covered the left part of the tool
       options bar). Fix in the ONE place every panel docks through: the column the panel would cover is checked against the controls that
       must stay reachable (RENDER + its zoom row, the colour row under it, the tool options bar, the Live Preview): a control at the panel's
       start pushes the top below it, a control further down caps the bottom above it (the panel scrolls inside, header + footer stay).
       1366x768 and 1920x1080 have a free gutter, so nothing moves there (measured: same x/y as before). */
    var KEEP = ['#renderFloat', '#btnRender', '#eyedropperDockTop', '#toolOptionsBar', '#splitPreview'];
    function piOff(n) { return !!(root.SPB_POLISH_I_OFF || (n && root['SPB_POLISH_I_' + n + '_OFF'])); }
    function keepClear(x, w, top, bot) {
        var rs = [], i, r;
        for (i = 0; i < KEEP.length; i++) { r = rect(KEEP[i]); if (r && r.right > x - 6 && r.left < x + w + 6) rs.push(r); }
        rs.sort(function (a, b) { return a.top - b.top; });
        var t = top, b = bot;
        for (i = 0; i < rs.length; i++) {
            r = rs[i];
            if (r.bottom + 6 <= t) continue;                                                 // already above the panel
            if (r.top < t + 140) t = Math.max(t, Math.ceil(r.bottom + 8));                   // in the panel's first rows: start below it
            else b = Math.min(b, Math.floor(r.top - 8));                                     // further down: stop above it
        }
        if (b - t < 260) b = bot;                                                            // never squeeze the panel below a usable height (the x rule keeps it off the Live Preview)
        return { top: t, bot: b };
    }
    function dockPos(el) {
        var vw = root.innerWidth, vh = root.innerHeight, w = el.offsetWidth || 352;
        var bar = rect('#spbTopToolbar'), top = Math.round(bar ? bar.bottom + 6 : 120);
        var src = rect('#splitSource'), prv = rect('#splitPreview'), cen = rect('#centerPanel');
        var L = Math.min(src ? src.left : 1e9, prv ? prv.left : 1e9), R = Math.max(src ? src.right : -1e9, prv ? prv.right : -1e9);
        if (L > 1e8) { L = cen ? cen.left : 0; R = cen ? cen.right : vw; }
        var x;
        if (L - 16 >= w) x = L - w - 10;                       // free gutter left of the canvases (1920: over the zone editor)
        else if (vw - R - 16 >= w) x = R + 10;                  // free gutter right of the canvases
        else x = 6;                                             // no gutter: Source side, never over the Live Preview
        if (KIT_IDS[el.id] && !t4off(4) && L - 16 >= w) { var zr0 = zoneRight(); if (zr0 > 0 && zr0 + 6 + w <= L - 10) x = zr0 + 6; }   // [TICKETS-4 item 4] the three kits share one spot, clear of the Zones column
        x = Math.max(4, Math.min(vw - w - 4, Math.round(x)));
        top = Math.max(4, Math.min(vh - 160, top));
        var bot = vh - 8;
        if (!piOff(1)) { var k = keepClear(x, w, top, bot); top = Math.max(4, Math.min(vh - 160, k.top)); bot = k.bot; }
        return { x: x, y: top, mh: Math.max(220, bot - top), bot: bot };
    }
    function setMH(el, mh, strong) {   // [POLISH-I] a bottom cap must beat the shell's own `max-height: calc(100vh - var(--ph-top) - 8px) !important`
        var v = mh + 'px';
        if (el.style.getPropertyValue('max-height') === v && (el.style.getPropertyPriority('max-height') === 'important') === !!strong) return;
        el.style.setProperty('max-height', v, strong ? 'important' : '');
    }
    function applyPos(el, p) {
        var vh = root.innerHeight;
        if (el.style.left !== p.x + 'px') el.style.left = p.x + 'px';
        if (el.style.top !== p.y + 'px') el.style.top = p.y + 'px';
        if (el.style.right) el.style.right = ''; if (el.style.bottom) el.style.bottom = ''; if (el.style.transform) el.style.transform = '';
        el.style.setProperty('--ph-top', p.y + 'px');
        setMH(el, p.mh, p.bot !== undefined && p.bot < vh - 8);
    }
    function placed(id) { var m = moved[id]; return m && typeof m === 'object' && isFinite(m.x) && isFinite(m.y) ? m : null; }
    /* [TICKETS-3 2026-10-10 items 1 + 5, lane TICKETS-3] kill switch window.SPB_T3_OFF, or window.SPB_T3_1_OFF (helper dock + resize) / window.SPB_T3_5_OFF (toasts).
       IQ3-2 + IQ3-7 (INTEGRATION-QA-3): the AI helper (#spbProAI) was placed ONCE when it opened (js/ui/spb-nuq-fix.js placeDock: a right-hand drawer): resized from 1920 to 1100 it sat at
       x 1514 = completely off-screen while "open"; opened at 1100 and widened it covered RENDER 96%; opened at 1100 it covered 51% of the Live Preview and 20% of the tool options bar.
       It now docks through the SAME shell as every other panel (free gutter left of the canvases at 1920, the Source side at 1100 under the colour row, never over RENDER / the
       Live Preview) and re-docks on every window resize. A helper the painter dragged or sized (its own spb_nuq_dock_user flag, or a header drag the shell remembered) stays where
       they put it and is only brought back inside the window. Double-click its header = dock again. */
    function t3off(n) { try { return !!(root.SPB_T3_OFF || (n && root['SPB_T3_' + n + '_OFF'])); } catch (_) { return false; } }
    var HELPER = 'spbProAI', UKEY = 'spb_nuq_dock_user';
    function ukeyPlaced() { try { return root.localStorage.getItem(UKEY) === '1'; } catch (_) { return false; } }
    function helperSkip() { var b = doc.body; return !b || t3off(1) || b.classList.contains('spb-chat-studio') || b.classList.contains('spb-easy-on'); }
    // ------------------------------------------------------------------------------------------------ [TICKETS-4 2026-10-10 item 2] the helper dock never covers RENDER or the canvas row
    /* UI-B (BURN-1010): the AI helper dock (#spbProAI) dragged by its header landed ON RENDER (covers 100%, 1100 + 1920) and over SOURCE / the Live Preview (up to 90% of SOURCE),
       and resized it grew over the Live Preview; its default spot at 1100 (x 6..358) hid 46% of SOURCE. Every dock / drop / resize of the helper now goes through fitHelper():
       the box is checked against RENDER + its zoom row (weight 1000), the colour row + tool options bar (20), the Live Preview (8) and SOURCE (4); with no overlap nothing changes
       (1920 default: same x/y as before). Otherwise the nearest spot of {current size, 300 wide, 260 tall} with the least weighted overlap wins. At 1100 there is no gutter wide enough for
       a 300 px panel, so it ends at the left edge (4..304): RENDER, its row and the Live Preview are never touched and SOURCE is covered 29% at most (was 46%), never half.
       Kill switch window.SPB_T4_OFF / SPB_T4_2_OFF. */
    var HB = [['#btnRender', 1000], ['#renderFloat', 1000], ['#eyedropperDockTop', 20], ['#toolOptionsBar', 20], ['#splitPreview', 8], ['#splitSource', 4]];
    function fitHelper(x, y, w, h) {
        var res = { x: x, y: y, w: w, h: h, changed: false };
        if (off() || t4off(2)) return res;
        var vw = root.innerWidth, vh = root.innerHeight, bl = [], i, r;
        for (i = 0; i < HB.length; i++) { r = rect(HB[i][0]); if (r) bl.push({ l: r.left, t: r.top, r: r.right, b: r.bottom, k: HB[i][1] }); }
        function cost(cx, cy, cw, ch) { var c = 0, j, o, ww, hh; for (j = 0; j < bl.length; j++) { o = bl[j]; ww = Math.min(cx + cw, o.r) - Math.max(cx, o.l); hh = Math.min(cy + ch, o.b) - Math.max(cy, o.t); if (ww > 0 && hh > 0) c += o.k * ww * hh; } return c; }
        if (cost(x, y, w, h) === 0) return res;
        var MINW = 320, MINH = 260, ws = [w], hs = [h], sizes = [], a, b, gl = 1e9, gr = -1e9, g;   // 320 = the panel's own css min-width
        for (i = 0; i < bl.length; i++) if (bl[i].k >= 4 && bl[i].k <= 8) { gl = Math.min(gl, bl[i].l); gr = Math.max(gr, bl[i].r); }   // the canvas row: the free gutters left / right of it
        if (w > MINW) ws.push(MINW);
        if (gl < 1e8) { g = Math.round(gl - 14); if (g >= MINW && g < w && ws.indexOf(g) < 0) ws.push(g); g = Math.round(vw - gr - 14); if (g >= MINW && g < w && ws.indexOf(g) < 0) ws.push(g); }
        if (h > MINH) hs.push(MINH);
        for (a = 0; a < ws.length; a++) for (b = 0; b < hs.length; b++) sizes.push([ws[a], hs[b]]);
        var best = null, bc = 1e18, s, cx, cy, c, cw, ch;
        for (s = 0; s < sizes.length; s++) {
            cw = Math.min(sizes[s][0], vw - 8); ch = Math.min(sizes[s][1], vh - 8);
            for (cx = 4; cx <= vw - cw - 4; cx += 6) for (cy = 4; cy <= vh - ch - 4; cy += 6) {
                c = cost(cx, cy, cw, ch) + Math.abs(cx - x) + Math.abs(cy - y) + (w - cw) * h + 2 * (h - ch) * w;   // narrowing the box is cheap, shortening it dearer
                if (c < bc) { bc = c; best = { x: cx, y: cy, w: cw, h: ch }; }
            }
        }
        if (!best) return res;
        res.x = best.x; res.y = best.y; res.w = best.w; res.h = best.h; res.changed = (best.x !== x || best.y !== y || best.w !== w || best.h !== h);
        return res;
    }
    var fitT = 0;
    function fitHelperSoon() {   // after the painter's own resize (CSS resize handle): wait until the size stops changing, then bring the box back clear of RENDER / the canvas row
        if (off() || t4off(2) || helperSkip()) return;
        if (fitT) clearTimeout(fitT);
        fitT = setTimeout(function () {
            fitT = 0; var st = state[HELPER], el = st && st.el; if (!st || !st.vis || st.drag || !visible(el)) return;
            var r = el.getBoundingClientRect(), f = fitHelper(Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height));
            if (f.changed) { moved[HELPER] = { x: f.x, y: f.y }; saveMoved(); if (!el.classList.contains('min')) { el.style.setProperty('width', f.w + 'px'); el.style.setProperty('height', f.h + 'px'); } dock(HELPER); }
        }, 380);
    }
    function dockHelper(id) {
        var st = state[id], el = st && st.el; if (!el || off() || helperSkip()) return;
        var vw = root.innerWidth, vh = root.innerHeight, m = placed(id), p, w, hh, mini = el.classList.contains('min');
        if (m || ukeyPlaced()) {   // the painter's place: keep it, only bring it back inside the window (a window that got smaller must never lose it)
            w = Math.max(300, Math.min(el.offsetWidth || 392, vw - 12));
            var r = el.getBoundingClientRect();
            var x = Math.max(4, Math.min(vw - w - 4, Math.round(m ? m.x : r.left))), y = Math.max(4, Math.min(vh - 120, Math.round(m ? m.y : r.top)));
            p = { x: x, y: y, mh: Math.max(180, vh - y - 8), bot: vh - 8 };
            hh = Math.min(el.offsetHeight || 560, p.mh);
            var f = fitHelper(x, y, w, hh);   // [TICKETS-4 item 2] never over RENDER / the canvas row
            if (f.changed) { x = f.x; y = f.y; w = f.w; hh = f.h; p = { x: x, y: y, mh: Math.max(hh, vh - y - 8), bot: vh - 8 }; if (m) { moved[id] = { x: x, y: y }; saveMoved(); } }
        } else {                   // docked like the tool panels (narrower under 1280 px, the same step the shell uses)
            w = vw < 1280 ? 352 : 392; w = Math.min(w, vw - 12);
            if (el.offsetWidth !== w) el.style.setProperty('width', w + 'px');
            p = dockPos(el); hh = p.mh;
            var f2 = fitHelper(p.x, p.y, w, hh);   // [TICKETS-4 item 2] 1100: 300 wide at the left edge (SOURCE 29% covered, was 46%)
            if (f2.changed) { p.x = f2.x; p.y = f2.y; w = f2.w; hh = f2.h; p.mh = Math.max(hh, vh - p.y - 8); p.bot = vh - 8; }
        }
        applyPos(el, p);
        if (el.offsetWidth !== w) el.style.setProperty('width', w + 'px');
        if (!mini) { var hs = Math.round(hh) + 'px'; if (el.style.height !== hs) el.style.setProperty('height', hs); }
        st.x = p.x; st.y = p.y; st.mh = p.mh;
    }
    function dock(id) {   // docked spot, or the spot the painter dragged it to (kept inside the window)
        var st = state[id], el = st && st.el; if (!el || off()) return;
        if (id === HELPER) { dockHelper(id); return; }   // [TICKETS-3 item 1]
        var p = dockPos(el), m = placed(id);
        if (m) {
            var vw = root.innerWidth, vh = root.innerHeight, w = el.offsetWidth || 352;
            p.x = Math.max(4, Math.min(vw - Math.min(w, 120) - 4, Math.round(m.x)));
            p.y = Math.max(4, Math.min(vh - 80, Math.round(m.y)));
            p.mh = Math.max(220, vh - p.y - 8); p.bot = vh - 8;   // where the painter put it is the painter's call: no keep-clear cap
        }
        applyPos(el, p);
        st.x = p.x; st.y = p.y; st.mh = p.mh;
    }
    function remember(id) {   // the painter put it here: keep it here (this session and next), double-click the header to dock it again
        var st = state[id], el = st && st.el; if (!el) return;
        var r = el.getBoundingClientRect(); moved[id] = { x: Math.round(r.left), y: Math.round(r.top) }; saveMoved(); dock(id);
    }
    function front(el) {
        if (off() || (el.id === HELPER && helperSkip())) return;
        doc.querySelectorAll('.spb-ph-front').forEach(function (n) { if (n !== el) n.classList.remove('spb-ph-front'); });
        el.classList.add('spb-ph-front');
    }
    function wireDrag(id, el, sel) {   // panels without a drag of their own
        el.addEventListener('pointerdown', function (e) {
            if (off() || e.button !== 0) return;
            var h = e.target.closest && e.target.closest(sel); if (!h || !el.contains(h)) return;
            if (e.target.closest('button, input, select, textarea, a, label')) return;
            var r = el.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top, go = false;
            if (state[id]) state[id].drag = true;   // check() must not snap it back to the dock mid-drag
            function mv(ev) {
                if (!go && Math.abs(ev.clientX - e.clientX) + Math.abs(ev.clientY - e.clientY) < 4) return;
                go = true; doc.body.classList.add('spb-ph-dragging');
                var x = Math.max(0, Math.min(root.innerWidth - 80, ev.clientX - dx)), y = Math.max(0, Math.min(root.innerHeight - 40, ev.clientY - dy));
                el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.right = ''; el.style.bottom = ''; el.style.transform = '';
                el.style.setProperty('--ph-top', y + 'px'); el.style.maxHeight = Math.max(220, root.innerHeight - y - 8) + 'px';
            }
            function up() { doc.removeEventListener('pointermove', mv); doc.removeEventListener('pointerup', up); doc.body.classList.remove('spb-ph-dragging'); if (state[id]) state[id].drag = false; if (go) remember(id); }
            doc.addEventListener('pointermove', mv); doc.addEventListener('pointerup', up);
        });
    }
    function attach(id) {
        var el = doc.getElementById(id); if (!el) return;
        var st = state[id];
        if (st && st.el === el) return;
        st = state[id] = { el: el, vis: false, busy: false };
        var cfg = PANELS[id];
        if (cfg.drag) wireDrag(id, el, cfg.drag);
        if (cfg.handle) {   // the panel drags itself: a real move of its header means the painter placed it
            el.addEventListener('pointerdown', function (e) {
                if (off() || e.button !== 0) return;
                var h = e.target.closest && e.target.closest(cfg.handle); if (!h || e.target.closest('button, input, select')) return;
                var x0 = e.clientX, y0 = e.clientY;
                if (state[id]) state[id].drag = true;   // its own drag is moving it: check() must not snap it back mid-drag
                function up(ev) {
                    doc.removeEventListener('pointerup', up, true);
                    var far = Math.abs(ev.clientX - x0) + Math.abs(ev.clientY - y0) > 6;
                    setTimeout(function () { if (state[id]) state[id].drag = false; if (far) remember(id); else dock(id); }, 0);   // after its own pointerup
                }
                doc.addEventListener('pointerup', up, true);
            }, true);
        }
        el.addEventListener('dblclick', function (e) {   // double-click the header: dock it again
            var hs = cfg.drag || cfg.handle; if (off() || !e.target.closest || !e.target.closest(hs) || e.target.closest('button, input, select')) return;
            delete moved[id]; saveMoved();
            if (id === HELPER) { try { root.localStorage.removeItem(UKEY); } catch (_) {} }   // [TICKETS-3 item 1] the helper's own "painter placed it" flag
            dock(id);
        });
        el.addEventListener('pointerdown', function () { front(el); }, true);
        if (id === HELPER && root.ResizeObserver) { try { new ResizeObserver(fitHelperSoon).observe(el); } catch (_) {} }   // [TICKETS-4 item 2] the painter resized it
        st.obs = new MutationObserver(function () { check(id); });
        st.obs.observe(el, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
        check(id);
    }
    function check(id) {
        var st = state[id]; if (!st) return;
        var v = visible(st.el);
        if (v && !st.vis) { st.vis = true; st.n = 0; front(st.el); dock(id); return; }
        if (!v) { st.vis = false; return; }
        if (st.drag || off()) return;
        // visible and its own code moved it (open / re-place / clamp): put it back at the dock, or where the painter put it.
        // [2026-10-10 real-load fix] no "busy" window any more: on a panel's FIRST open (Car-Space Fade builds its panel then
        // re-places it in the same tick) the re-place landed inside that window and the panel stayed at the window corner.
        // Our own writes match st.x / st.y, so they never trigger a re-dock; a panel that keeps re-placing itself is left alone
        // after 30 re-docks in a second (no ping-pong loop).
        if (st.el.style.left === st.x + 'px' && st.el.style.top === st.y + 'px') return;
        var now = Date.now(); if (!st.win || now - st.win > 1000) { st.win = now; st.n = 0; }
        if (++st.n > 30) return;
        dock(id);
    }
    function scan() {
        for (var id in PANELS) attach(id);
        watchLayout(); tidyToasts();   // [TICKETS-3 item 5]
        t4Classes();   // [TICKETS-4 item 6]
        var cw = doc.getElementById('spbCwStudio');
        if (cw && !cw.__phFront) { cw.__phFront = 1; cw.addEventListener('pointerdown', function () { front(cw); }, true); new MutationObserver(function () { if (visible(cw) && !cw.__phVis) { cw.__phVis = 1; front(cw); } else if (!visible(cw)) cw.__phVis = 0; }).observe(cw, { attributes: true, attributeFilter: ['style', 'class'] }); }
        // a Race Wear panel (REV-WEAR, in progress) joins the shell when it appears with role=dialog
        var wp = doc.querySelector('[id^="spbWear"][role="dialog"], [id^="spbRevWear"][role="dialog"]');
        if (wp && !PANELS[wp.id]) { PANELS[wp.id] = {}; wp.classList.add('spb-ph-panel'); attach(wp.id); }
    }
    root.addEventListener('resize', function () { for (var id in state) if (state[id].vis) dock(id); resizeTrail(); });
    // [TICKETS-3 2026-10-10 item 1] a debounced second pass once the page has re-flowed (the controls the dock keeps clear of move after the first resize event):
    // every visible docked panel (the AI helper too), every registered onLayout panel, the tool-name hint and the stale-version banner are placed again.
    var rzT = 0;
    function resizeTrail() {
        if (t3off(1) && t3off(5)) return;
        if (rzT) clearTimeout(rzT);
        rzT = setTimeout(function () {
            rzT = 0; if (off()) return;
            for (var id in state) { var st = state[id]; if (st.vis && !st.drag) dock(id); }
            for (var i = 0; i < layoutHooks.length; i++) { try { layoutHooks[i](); } catch (_) {} }
            tidyToasts();
        }, 140);
    }
    // [POLISH-I 2026-10-10 item 1] the controls the dock keeps clear (KEEP) can change size while a panel is open (the colour row under RENDER comes and goes
    // with the tool, the shell re-flows): re-dock the visible panels, and any panel that registered with onLayout() (Spec Sculpt), when they do.
    var layoutHooks = [], roSeen = [], roRaf = 0, roObs = null;
    function relayout() {
        if (roRaf) return;
        roRaf = root.requestAnimationFrame(function () {
            roRaf = 0; if (piOff(1) || off()) return;
            for (var id in state) { var st = state[id]; if (st.vis && !st.drag) dock(id); }
            for (var i = 0; i < layoutHooks.length; i++) { try { layoutHooks[i](); } catch (_) {} }
            tidyToasts();
        });
    }
    function watchLayout() {
        if (!root.ResizeObserver) return;
        if (!roObs) roObs = new ResizeObserver(relayout);
        KEEP.concat(['#previewBottomBar']).forEach(function (sel) { var e = doc.querySelector(sel); if (e && roSeen.indexOf(e) < 0) { roSeen.push(e); roObs.observe(e); } });
    }

    // ------------------------------------------------------------------------------------------------ [TICKETS-3 2026-10-10 item 5] two toasts that sat on controls
    /* POLISH-I measured: the tool-name hint (#platinumToolFlash, placed under the active tool button by js/ui/spb-polish-f.js) covered RENDER at 1100 (4092 px2) and still did
       at 1366 (3036) and 1920 (3168); the stale-version banner (#spbStaleBanner, js/spb-mcp-bridge.js, fixed right 16 / bottom 16) covered the tool options bar at 1100 (3519 px2) and
       1366, and the AI pill at the bottom right. Both are placed by other lanes' code, so they are only MOVED here, after that code has placed them:
         hint   -> left of what it would cover when there is room, else just below those rows, else right of them (never over RENDER, its zoom row, the colour row, the options bar);
         banner -> lifted above the options bar / AI pill when it sits over them.
       Kill switch window.SPB_T3_OFF / SPB_T3_5_OFF. */
    var BLOCK = ['#btnRender', '#renderFloat', '#eyedropperDockTop', '#toolOptionsBar'];
    function blockers() { var out = [], i, r; for (i = 0; i < BLOCK.length; i++) { r = rect(BLOCK[i]); if (r) out.push(r); } return out; }
    function hitsOf(x, y, w, h, bl) { return bl.filter(function (r) { return x < r.right + 2 && x + w > r.left - 2 && y < r.bottom + 2 && y + h > r.top - 2; }); }
    function mx(a, f) { var v = -1e9; for (var i = 0; i < a.length; i++) v = Math.max(v, f(a[i])); return v; }
    function mn(a, f) { var v = 1e9; for (var i = 0; i < a.length; i++) v = Math.min(v, f(a[i])); return v; }
    function clearTip() {
        if (off() || t3off(5)) return;
        var el = doc.getElementById('platinumToolFlash'); if (!el || el.__t3mv || el.style.opacity === '0' || getComputedStyle(el).display === 'none') return;
        var r = el.getBoundingClientRect(); if (r.width < 20 || r.height < 10) return;
        var bl = blockers(), vw = root.innerWidth, vh = root.innerHeight, x = r.left, y = r.top, w = r.width, h = r.height, hit = hitsOf(x, y, w, h, bl);
        if (!hit.length) return;
        var nx = null, ny = null, lx = mn(hit, function (q) { return q.left; }) - 8 - w;
        if (lx >= 8 && !hitsOf(lx, y, w, h, bl).length) { nx = lx; ny = y; }
        if (nx === null) {   // just below the rows it hit (keep stepping while a lower control is in the way)
            var ty = y; for (var k = 0; k < 6; k++) { var hh = hitsOf(x, ty, w, h, bl); if (!hh.length) break; ty = mx(hh, function (q) { return q.bottom; }) + 8; }
            if (ty + h <= vh - 8 && !hitsOf(x, ty, w, h, bl).length) { nx = x; ny = ty; }
        }
        if (nx === null) { var rx = mx(hit, function (q) { return q.right; }) + 8; if (rx + w <= vw - 8 && !hitsOf(rx, y, w, h, bl).length) { nx = rx; ny = y; } }
        if (nx === null) return;
        el.__t3mv = true;
        try { el.style.setProperty('left', Math.round(nx) + 'px', 'important'); el.style.setProperty('top', Math.round(ny) + 'px', 'important'); el.style.setProperty('--pf-caret', '18px'); }
        finally { el.__t3mv = false; }
    }
    function tidyBanner() {
        if (off() || t3off(5)) return;
        var b = doc.getElementById('spbStaleBanner'); if (!b || !b.getClientRects().length) return;
        var vw = root.innerWidth, vh = root.innerHeight, r0 = b.getBoundingClientRect(), left = r0.left, w = r0.width, h = r0.height, top0 = vh - 16 - h, top = 1e9, q;
        var pills = [rect('#toolOptionsBar'), rect('#spbProAIFab')];
        for (var i = 0; i < pills.length; i++) { q = pills[i]; if (q && q.right > left - 2 && q.left < left + w + 2 && q.bottom > top0 - 2 && q.top < top0 + h + 2) top = Math.min(top, q.top); }
        var bot = top < 1e9 ? Math.max(16, Math.round(vh - top + 8)) : 16;
        if (bot + h > vh - 8) bot = 16;
        // the clean-default skin pins the banner with "bottom:16px !important": the lifted value has to be important too
        if (b.style.getPropertyValue('bottom') !== bot + 'px' || b.style.getPropertyPriority('bottom') !== 'important') b.style.setProperty('bottom', bot + 'px', 'important');
    }
    // ------------------------------------------------------------------------------------------------ [TICKETS-4 2026-10-10 item 1] the AI pill sat on the Layers action row and the Settings menu
    /* UI-B (BURN-1010) measured: #spbProAIFab (fixed, right 18 / bottom 18, css/spb-pro-ai-20260930.css) covered 470 px2 of the Layers panel's bottom action row (.tlay2-bar)
       at 1100x800 and 1947 px2 of the Settings dropdown (#settingsDropdown, 746..1086 x 52..788 at 1100; down to the window bottom at 1920) rows. The pill's own file is not ours,
       so it is only MOVED here: when its home corner would sit on a must-clear surface (FAB_KEEP) it takes the nearest spot in the lower-right of the window that covers the
       fewest controls (buttons, inputs, canvases, layer rows) and none of the must-clear ones; it goes home again when the surface closes. Kill switch window.SPB_T4_OFF / SPB_T4_1_OFF. */
    function t4off(n) { try { return !!(root.SPB_T4_OFF || (n && root['SPB_T4_' + n + '_OFF'])); } catch (_) { return false; } }
    // [TICKETS-4 2026-10-10 item 6] the Car submenu inside the folded "Menus" panel (<=1300 px wide) wraps its long labels instead of clipping them (css/spb-polish-h-20261010.css, TICKETS-4 item 6 block). Kill switch SPB_T4_OFF / SPB_T4_6_OFF -> body.spb-t4-6-off.
    function t4Classes() { try { doc.body.classList.toggle('spb-t4-6-off', t4off(6)); doc.body.classList.toggle('spb-t4-9-off', t4off(9)); doc.body.classList.toggle('spb-t4-10-off', t4off(10)); } catch (_) {} }   // item 9 = Settings dropdown (license hint, one scroller); item 10 = Spec / Material brush bar labels
    var FAB_KEEP = ['.tlay2-bar', '#settingsDropdown'], fabMoved = false, fabHomeOff = null;
    function ovl(a, b) { var w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top); return w > 0 && h > 0 ? w * h : 0; }
    function fabHome() {
        var fab = doc.getElementById('spbProAIFab'); if (!fab) return;
        if (fabMoved) { fab.style.removeProperty('right'); fab.style.removeProperty('bottom'); fab.style.removeProperty('transition'); fabMoved = false; }
    }
    function tidyFab() {
        var fab = doc.getElementById('spbProAIFab');
        if (!fab) return;
        if (off() || t4off(1)) { fabHome(); return; }
        if (!visible(fab)) return;
        var vw = root.innerWidth, vh = root.innerHeight;
        var fr = fab.getBoundingClientRect(), w = fr.width, h = fr.height, keep = [], i, r, e;
        if (!fabMoved) fabHomeOff = { r: vw - fr.right, b: vh - fr.bottom };   // the css corner, remembered while the pill is at home (never re-measured at a moved spot: no flicker)
        var ho = fabHomeOff || { r: 18, b: 18 };
        var pan = null;
        for (i = 0; i < FAB_KEEP.length; i++) { e = doc.querySelector(FAB_KEEP[i]); if (e && visible(e)) { r = e.getBoundingClientRect(); if (r.width > 4 && r.height > 4) { keep.push(r); if (i === 0) { var pe = e.closest('#rightPanel'); if (pe) pan = pe.getBoundingClientRect(); } } } }   // the Layers action row: its whole panel is crowded, so the pill leaves the panel when it can
        var home = { left: vw - ho.r - w, top: vh - ho.b - h, right: vw - ho.r, bottom: vh - ho.b }, hit = false;
        for (i = 0; i < keep.length; i++) if (ovl(home, { left: keep[i].left - 4, top: keep[i].top - 4, right: keep[i].right + 4, bottom: keep[i].bottom + 4 })) hit = true;
        if (!hit) { fabMoved = false; return; }
        var ctl = [], nodes = doc.querySelectorAll('button,input,select,textarea,a[href],summary,canvas,[role=button],[role=tab],[role=menuitem],[role=slider],.layer-row');
        for (i = 0; i < nodes.length; i++) {
            e = nodes[i]; if (e === fab || fab.contains(e) || !e.getClientRects().length) continue;
            r = e.getBoundingClientRect(); if (r.width < 6 || r.height < 6 || r.right < 0 || r.bottom < 0 || r.left > vw || r.top > vh) continue;
            ctl.push(r);
        }
        var best = null, bc = 1e18, x2, y2, c, d, j, cand;
        for (x2 = vw - ho.r; x2 >= Math.max(w + 8, vw * 0.35); x2 -= 10) {
            for (y2 = vh - ho.b; y2 >= Math.max(h + 8, vh * 0.45); y2 -= 10) {
                cand = { left: x2 - w, top: y2 - h, right: x2, bottom: y2 }; c = 0;
                for (j = 0; j < keep.length; j++) c += 400 * ovl(cand, { left: keep[j].left - 4, top: keep[j].top - 4, right: keep[j].right + 4, bottom: keep[j].bottom + 4 });
                for (j = 0; j < ctl.length; j++) c += 8 * ovl(cand, ctl[j]);
                if (pan && hit) c += 40 * ovl(cand, pan);
                d = Math.abs(vw - ho.r - x2) + Math.abs(vh - ho.b - y2); c += d * 0.15;
                if (c < bc) { bc = c; best = cand; }
            }
        }
        if (!best) return;
        fab.style.setProperty('transition', 'right .18s ease, bottom .18s ease', 'important');
        fab.style.setProperty('right', Math.round(vw - best.right) + 'px', 'important');
        fab.style.setProperty('bottom', Math.round(vh - best.bottom) + 'px', 'important');
        fabMoved = true;
    }
    var fabT = 0;
    function fabSoon() { if (fabT) return; fabT = setTimeout(function () { fabT = 0; try { tidyFab(); } catch (e) { console.warn('[polish-h] fab', e); } }, 90); }
    doc.addEventListener('click', function () { fabSoon(); setTimeout(fabSoon, 450); }, true);
    root.addEventListener('resize', function () { fabSoon(); setTimeout(fabSoon, 400); });
    // ------------------------------------------------------------------------------------------------ [TICKETS-4 2026-10-10 item 4] one dock spot for Number Kit / Sponsor Kit / League Pack
    /* UI-A (BURN-1010): at 1920 the Number + Sponsor kits docked at x 314 (352 wide, right-aligned to the Source gutter) and the League Pack at x 26 (640 wide), over the Zones
       column; at 1100 the League Pack (640 x 585, mostly empty with no drivers) covered SOURCE 100% and the Live Preview 34%. Now the three share ONE dock: top-left just right of the
       Zones column (x = Zones column right + 6, y under the tool band) at 1920; the League Pack takes the rest of that gutter (470 wide; its roster table scrolls sideways when narrow),
       hugs its content in height (no empty slab), and at 1100 (no gutter) is 336 wide like the other kits and the stage shows the Live Preview only while it is open (temporary view,
       handed back on close) so it covers neither SOURCE nor the Live Preview. Kill switch window.SPB_T4_OFF / SPB_T4_4_OFF. */
    var KIT_IDS = { spbNumKit: 1, spbSponsorKit: 1, spbLeaguePack: 1 };
    function zoneRight() { var z = rect('#leftPanel'); return z ? Math.round(z.right) : 0; }
    function t4League(el) {
        try { doc.body.classList.toggle('spb-t4-4-off', !!(root.SPB_T4_OFF || root.SPB_T4_4_OFF)); } catch (_) {}
        if (t4off(4)) { ['width', 'height'].forEach(function (k) { el.style.removeProperty(k); }); el.classList.remove('spb-t4-lg-narrow', 'spb-t4-lg-tight'); return; }
        var vw = root.innerWidth, src = rect('#splitSource'), prv = rect('#splitPreview'), L = Math.min(src ? src.left : 1e9, prv ? prv.left : 1e9), zr = zoneRight(), w = 640;
        var gut = L < 1e8 ? Math.floor(L - 10 - (zr + 6)) : 0;
        if (gut >= 420) w = Math.min(640, gut);                 // 1920: the gutter between the Zones column and SOURCE
        else w = vw < 1280 ? 336 : 352;                          // no gutter: the same width as the other kits
        w = Math.min(w, vw - 12);
        if (el.style.getPropertyValue('width') !== w + 'px') el.style.setProperty('width', w + 'px', 'important');
        if (el.style.getPropertyValue('height') !== 'auto') el.style.setProperty('height', 'auto', 'important');   // content height (css had min(640px, ...))
        el.classList.toggle('spb-t4-lg-narrow', w < 600); el.classList.toggle('spb-t4-lg-tight', w < 420);
    }
    function t4LeagueView(el) {   // 1100: the docked panel would sit over SOURCE -> show the Live Preview only while it is open
        if (t4off(4) || !el.isConnected) return;
        var PG = root.__spbPolishG, src = rect('#splitSource'); if (!PG || !PG.state || !src) return;
        var pr = el.getBoundingClientRect();
        if (el.__t4view || !(pr.right > src.left + 4 && pr.left < src.right - 4 && pr.bottom > src.top + 4 && pr.top < src.bottom - 4)) return;
        var e = PG.state().eff; if (e !== 'split' && e !== 'source') return;
        PG.setMode('preview', false); el.__t4view = true;
        if (!el.__t4mo && root.MutationObserver) {
            el.__t4mo = new MutationObserver(function () {
                if (el.__t4view && (el.style.display === 'none' || !el.isConnected)) { el.__t4view = false; try { root.__spbPolishG.clearTmp(); } catch (_) {} }
            });
            el.__t4mo.observe(el, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
        }
    }
    var tipObs = null;
    function watchTip() {
        var el = doc.getElementById('platinumToolFlash');
        if (!el || el.__t3obs || !root.MutationObserver) return;
        el.__t3obs = true; tipObs = new MutationObserver(function () { clearTip(); }); tipObs.observe(el, { attributes: true, attributeFilter: ['style'] });
    }
    function tidyToasts() { try { watchTip(); clearTip(); tidyFab(); tidyBanner(); } catch (e) { console.warn('[polish-h] toasts', e); } }

    // ------------------------------------------------------------------------------------------------ boot + kill switch
    var raf = 0;
    function schedule() { if (!raf) raf = requestAnimationFrame(function () { raf = 0; try { syncMenus(); } catch (e) { console.warn('[polish-h] menus', e); } }); }
    function start() {
        if (root.SPB_POLISH_H_OFF && doc.body) doc.body.classList.add('spb-polish-h-off');
        syncMenus(); scan();
        var bar = doc.getElementById('spbTopToolbar');
        if (bar) new MutationObserver(schedule).observe(bar, { childList: true, subtree: true });
        new MutationObserver(function () {
            schedule();
            for (var id in state) {
                var st = state[id];
                if (off() && st.el) { if (st.mh && st.el.style.maxHeight === st.mh + 'px') st.el.style.maxHeight = ''; st.el.style.removeProperty('--ph-top'); st.el.classList.remove('spb-ph-front'); }
                check(id);
            }
        }).observe(doc.body, { attributes: true, attributeFilter: ['class'] });
        new MutationObserver(function (ms) { for (var i = 0; i < ms.length; i++) if (ms[i].addedNodes.length) { scan(); break; } }).observe(doc.body, { childList: true });
        setInterval(function () { scan(); schedule(); }, 1500);   // tools build their panels / menu entries lazily
    }
    root.__spbPolishH = { version: VERSION, dock: dock, dockPos: dockPos, isOff: off, applyDock: function (el) { if (off() || !el) return null; if (el.id === 'spbLeaguePack') t4League(el); var p = dockPos(el); applyPos(el, p); if (el.id === 'spbLeaguePack') t4LeagueView(el); return p; }, onLayout: function (fn) { layoutHooks.push(fn); watchLayout(); }, sync: syncMenus, tidyToasts: tidyToasts, moved: moved, state: state, reset: function () { for (var k in moved) delete moved[k]; saveMoved(); for (var id in state) if (state[id].vis) dock(id); } };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { setTimeout(start, 0); });
    else setTimeout(start, 0);
})();
