/* [SPB-TLAY2 2026-10-10] TOOLS-LAYERS-2 lane. L2-1 THE BUTTON WALL.
 *
 * The selected layer card in the right Layers panel ended in ~20 same-weight text buttons (Dupe / Merge / Rename / Mirror / Stroke FX / Export /
 * Make Zone / Delete / Solo / Flip H / Flip V / Rot 90 / Move / Xform / Pan / Fit / Lock Zone / FX x / Done; paint-booth-3-canvas.js
 * renderLayerPanel, ~192 px tall, five rows of orange / pink / gold / green text chips). It read as vibecoded.
 *
 * Now: ONE row of the five most used actions as monochrome line icons (Duplicate, Mirror Clone, Free Transform, Merge Down, Delete) with
 * tooltips + key hints, and a "More" button that opens a grouped menu (Arrange / Transform / Effects / Output) listing EVERY action with its
 * icon and key hint. Title Case, 28 px hit targets, teal focus ring, no orange. Card height before -> after: see PROGRESS.md.
 *
 * Nothing is re-implemented: this file runs after renderLayerPanel(), lifts the ORIGINAL buttons out of the card (they keep their inline
 * handlers, titles and disabled state) and every icon / menu row dispatches a real click (with Shift / Alt / Ctrl) on the original. Same handlers,
 * same undo steps. "Done" (deselect the layer; Esc no longer does it since TA-023) moves to the foot of the menu as "Deselect Layer".
 *
 * Kill switch: window.SPB_TLAY2_OFF = true (or localStorage SPB_TLAY2_OFF = '1') -> the next renderLayerPanel() leaves the card untouched.
 * Loaded AFTER pc-groups.js (the last renderLayerPanel wrapper) so the card is complete when it is restructured.
 */
(function () {
    'use strict';
    if (window.SPBTlay2Card) { if (typeof window.SPBTlay2Card.uninstall === 'function') window.SPBTlay2Card.uninstall(); else return; }   // re-load (dev hot install) replaces the previous copy
    var lsOff = false;
    try { lsOff = localStorage.getItem('SPB_TLAY2_OFF') === '1'; } catch (_e) { }
    if (lsOff && window.SPB_TLAY2_OFF !== true) window.SPB_TLAY2_OFF = true;
    function off() { return window.SPB_TLAY2_OFF === true; }
    var stats = { decorated: 0, lastMs: 0, fired: 0 };

    // ------------------------------------------------------------------ icons (16 px grid, 1.5 px line, currentColor)
    function svg(inner) { return '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + inner + '</svg>'; }
    var IC = {
        dupe: svg('<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.2A1.2 1.2 0 0 0 9.3 2H3.7A1.7 1.7 0 0 0 2 3.7v5.6A1.2 1.2 0 0 0 3.2 10.5"/>'),
        mirror: svg('<path d="M8 1.5v13" stroke-dasharray="1.7 1.7"/><rect x="2" y="5" width="4" height="6" rx="1"/><rect x="10" y="5" width="4" height="6" rx="1" stroke-dasharray="2.2 1.6"/>'),
        xform: svg('<rect x="4.5" y="4.5" width="7" height="7" rx=".5"/><rect x="1.8" y="1.8" width="2.6" height="2.6" rx=".4"/><rect x="11.6" y="1.8" width="2.6" height="2.6" rx=".4"/><rect x="1.8" y="11.6" width="2.6" height="2.6" rx=".4"/><rect x="11.6" y="11.6" width="2.6" height="2.6" rx=".4"/>'),
        solo: svg('<rect x="1.8" y="1.8" width="12.4" height="12.4" rx="2.2" stroke-dasharray="2.4 2"/><rect x="5.4" y="5.4" width="5.2" height="5.2" rx="1"/>'),
        merge: svg('<path d="M8 1.6v6.6M5.2 5.8 8 8.6l2.8-2.8"/><path d="M2.5 11.2h11M2.5 14h11"/>'),
        trash: svg('<path d="M2.5 4h11M6 4V2.4h4V4"/><path d="M3.9 4l.7 9.6h6.8L12.1 4"/><path d="M6.7 6.6v4.6M9.3 6.6v4.6"/>'),
        more: '<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true" focusable="false"><circle cx="3.2" cy="8" r="1.25"/><circle cx="8" cy="8" r="1.25"/><circle cx="12.8" cy="8" r="1.25"/></svg>',
        rename: svg('<path d="M2.4 13.6l.7-3.1 7.7-7.7a1.5 1.5 0 0 1 2.1 2.1l-7.7 7.7z"/><path d="M9.6 4l2.4 2.4"/>'),
        move: svg('<path d="M8 1.6v12.8M1.6 8h12.8"/><path d="M6 3.6 8 1.6l2 2M6 12.4l2 2 2-2M3.6 6 1.6 8l2 2M12.4 6l2 2-2 2"/>'),
        fliph: svg('<path d="M8 1.5v13" stroke-dasharray="1.7 1.7"/><path d="M6.2 4.2 2 8l4.2 3.8z" fill="currentColor" fill-opacity=".28"/><path d="M9.8 4.2 14 8l-4.2 3.8z"/>'),
        flipv: svg('<path d="M1.5 8h13" stroke-dasharray="1.7 1.7"/><path d="M4.2 6.2 8 2l3.8 4.2z" fill="currentColor" fill-opacity=".28"/><path d="M4.2 9.8 8 14l3.8-4.2z"/>'),
        rot: svg('<path d="M13.2 8A5.2 5.2 0 1 1 11.6 4.3"/><path d="M13.4 2.2v3.2h-3.2"/>'),
        pan: svg('<circle cx="8" cy="8" r="3.2"/><path d="M8 1.5v2.4M8 12.1v2.4M1.5 8h2.4M12.1 8h2.4"/>'),
        fit: svg('<path d="M2 5.4V2h3.4M10.6 2H14v3.4M14 10.6V14h-3.4M5.4 14H2v-3.4"/>'),
        stroke: svg('<rect x="2.2" y="2.2" width="11.6" height="11.6" rx="2.4"/><rect x="5.4" y="5.4" width="5.2" height="5.2" rx="1" stroke-opacity=".55"/>'),
        fx: svg('<path d="M2 5h12M2 11h12"/><circle cx="5.8" cy="5" r="1.7" fill="currentColor" fill-opacity=".25"/><circle cx="10.4" cy="11" r="1.7" fill="currentColor" fill-opacity=".25"/>'),
        exp: svg('<path d="M8 10.2V2M5.2 4.8 8 2l2.8 2.8"/><path d="M2.4 9.6v3.9h11.2V9.6"/>'),
        zone: svg('<rect x="1.8" y="1.8" width="12.4" height="12.4" rx="2.2" stroke-dasharray="2.4 2"/><path d="M8 5.2v5.6M5.2 8h5.6"/>'),
        lock: svg('<rect x="3.4" y="7" width="9.2" height="6.6" rx="1.5"/><path d="M5.5 7V5.2a2.5 2.5 0 0 1 5 0V7"/>'),
        raster: svg('<rect x="2.4" y="2.4" width="11.2" height="11.2" rx="1.5"/><path d="M2.4 6.1h11.2M2.4 9.9h11.2M6.1 2.4v11.2M9.9 2.4v11.2"/>'),
        done: svg('<path d="M3.6 3.6l8.8 8.8M12.4 3.6l-8.8 8.8"/>'),
        check: svg('<path d="M3 8.4 6.4 12 13 4.4"/>')
    };

    // ------------------------------------------------------------------ the action table
    // re: matched against the ORIGINAL button's inline onclick. icon: key in IC. tip: tooltip / aria-label for the icon button.
    var ACT = {
        dupe:   { re: /duplicateLayer/, label: 'Duplicate Layer', icon: 'dupe', key: 'Shift: Offset', tip: 'Duplicate Layer (Shift-click: +50 px offset copy)' },
        mirror: { re: /mirrorCloneLayer/, label: 'Mirror Clone', icon: 'mirror', key: '', tip: 'Mirror Clone: duplicate and flip to the opposite side of the car' },
        merge:  { re: /mergeLayerDown/, label: 'Merge Down', icon: 'merge', key: 'Ctrl+E', tip: 'Merge Down (Ctrl+E): merge into the layer below' },
        solo:   { re: /toggleLayerSolo/, label: 'Solo Layer', icon: 'solo', key: 'Alt+Eye', tip: 'Solo Layer: hide every other layer, click again to restore (Alt-click the eye)', toggle: true },
        rename: { re: /renameLayer\(/, label: 'Rename', icon: 'rename', key: 'Dbl-click', tip: 'Rename this layer (double-click the name)' },
        del:    { re: /deleteLayer\(/, label: 'Delete Layer', icon: 'trash', key: '', tip: 'Delete Layer (Ctrl+Z brings it back)', danger: true },
        move:   { re: /layer-move/, label: 'Move', icon: 'move', key: 'V', tip: 'Move: drag this layer on the canvas (V)' },
        xform:  { re: /activateContextTransform/, label: 'Free Transform', icon: 'xform', key: 'Ctrl+T', tip: 'Free Transform (Ctrl+T): scale, rotate, skew the layer, or just the selection' },
        fliph:  { re: /flipLayerH/, label: 'Flip Horizontal', icon: 'fliph', key: '', tip: 'Flip this layer horizontally' },
        flipv:  { re: /flipLayerV/, label: 'Flip Vertical', icon: 'flipv', key: '', tip: 'Flip this layer vertically' },
        rot:    { re: /rotateLayer90/, label: 'Rotate 90°', icon: 'rot', key: '', tip: 'Rotate this layer 90° clockwise' },
        pan:    { re: /panToLayer\([^)]*false\s*\)/, label: 'Pan to Layer', icon: 'pan', key: '', tip: 'Pan the view to this layer' },
        fit:    { re: /panToLayer\([^)]*true\s*\)/, label: 'Fit to Layer', icon: 'fit', key: '', tip: 'Zoom the view to fit this layer' },
        stroke: { re: /openLayerEffects/, label: 'Stroke FX…', icon: 'stroke', key: '', tip: 'Stroke FX: non-destructive outline with live preview' },
        fx:     { re: /setEffectIntensity/, label: 'FX Strength', icon: 'fx', key: 'Click: Cycle', tip: 'FX Strength: scales every layer effect (click cycles, Shift-click resets to 1.00)', keep: true },
        exp:    { re: /exportLayerAsPng/, label: 'Export as PNG', icon: 'exp', key: '', tip: 'Save just this layer as a transparent PNG (effects and adjustments baked in)' },
        zone:   { re: /makeZoneFromLayer/, label: 'Make Zone from Layer', icon: 'zone', key: '', tip: 'Create a zone restricted to this layer\'s footprint' },
        lock:   { re: /lockActiveZoneToSelectedLayer/, label: 'Lock Zone to Layer', icon: 'lock', key: 'Ctrl+L', tip: 'Lock the active zone to this layer\'s pixels (Ctrl+L)' },
        raster: { re: /SPBTextEdit\.rasterize/, label: 'Rasterize Text', icon: 'raster', key: '', tip: 'Turn live text into plain pixels (Ctrl+Z undoes)' },
        done:   { re: /deselectLayer/, label: 'Deselect Layer', icon: 'done', key: '', tip: 'Deselect this layer' }
    };
    var ORDER = ['dupe', 'mirror', 'merge', 'solo', 'rename', 'del', 'move', 'xform', 'fliph', 'flipv', 'rot', 'pan', 'fit', 'stroke', 'fx', 'exp', 'zone', 'lock', 'raster', 'done'];
    var PRIMARY = ['dupe', 'mirror', 'xform', 'merge', 'del'];   // five, so the row (+ More) still fits the 177 px card at a 1100 px window
    var GROUPS = [
        { g: 'Arrange', items: ['dupe', 'mirror', 'merge', 'solo', 'rename', 'del'] },
        { g: 'Transform', items: ['move', 'xform', 'fliph', 'flipv', 'rot', 'pan', 'fit'] },
        { g: 'Effects', items: ['stroke', 'fx'] },
        { g: 'Output', items: ['exp', 'zone', 'lock', 'raster'] },
        { g: '', items: ['done'] }
    ];

    function keyOf(btn) {
        var oc = btn.getAttribute('onclick') || '';
        if (!oc) return null;
        for (var i = 0; i < ORDER.length; i++) { var a = ACT[ORDER[i]]; if (a.re.test(oc)) return ORDER[i]; }
        return null;
    }
    function el(tag, cls, attrs, html) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (attrs) for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k) && attrs[k] != null) e.setAttribute(k, attrs[k]);
        if (html != null) e.innerHTML = html;
        return e;
    }
    // a real click on the original button: Shift / Alt / Ctrl carry over so "event.shiftKey ? offset copy : copy" and the FX reset keep working
    function fire(src, ev) {
        if (!src || src.disabled) return false;
        stats.fired++;
        var me;
        try { me = new MouseEvent('click', { bubbles: false, cancelable: true, view: window, shiftKey: !!(ev && ev.shiftKey), altKey: !!(ev && ev.altKey), ctrlKey: !!(ev && ev.ctrlKey), metaKey: !!(ev && ev.metaKey) }); }
        catch (_e) { src.click(); return true; }
        src.dispatchEvent(me);
        return true;
    }
    function soloOn(id) { try { return !!(_layerSoloVisibilitySnapshot && _layerSoloVisibilitySnapshot.layerId === id); } catch (_e) { return false; } }
    function fxVal() { try { return window.spbLayerFlow.getEffectIntensity(); } catch (_e) { return 1; } }
    function fxText() { var k = fxVal(); return '× ' + k.toFixed(2); }

    // ------------------------------------------------------------------ the overflow menu
    var menuState = null;   // { menu, trigger, srcs }
    function closeMenu(refocus) {
        var m = menuState; menuState = null;
        if (!m) return;
        document.removeEventListener('mousedown', m.onDown, true);
        document.removeEventListener('keydown', m.onKey, true);
        window.removeEventListener('resize', m.onClose, true);
        if (m.scroller) m.scroller.removeEventListener('scroll', m.onClose, true);
        if (m.menu.parentNode) m.menu.parentNode.removeChild(m.menu);
        if (m.trigger) { m.trigger.setAttribute('aria-expanded', 'false'); if (refocus && m.trigger.isConnected) { try { m.trigger.focus(); } catch (_e) { } } }
    }
    function openMenu(trigger, srcs, layerId) {
        closeMenu(false);
        var menu = el('div', 'tlay2-menu', { role: 'menu', 'aria-label': 'Layer Actions' });
        var rows = [];
        GROUPS.forEach(function (grp, gi) {
            var present = grp.items.filter(function (k) { return srcs[k]; });
            if (!present.length) return;
            if (gi > 0) menu.appendChild(el('div', 'tlay2-sep', { role: 'separator' }));
            if (grp.g) menu.appendChild(el('div', 'tlay2-glab', { role: 'presentation' }, grp.g));
            present.forEach(function (k) {
                var a = ACT[k], s = srcs[k];
                var label = a.label;
                var isSolo = k === 'solo' && soloOn(layerId);
                if (isSolo) label = 'Restore Layers';
                var row = el('button', 'tlay2-mi' + (a.danger ? ' tlay2-danger' : ''), { type: 'button', role: 'menuitem', tabindex: '-1', 'data-t2': k, title: s.disabled ? (s.title || a.tip) : a.tip },
                    '<span class="tlay2-mi-ic">' + IC[a.icon] + '</span><span class="tlay2-mi-lab">' + label + '</span>' +
                    (k === 'fx' ? '<span class="tlay2-mi-key tlay2-fxval">' + fxText() + '</span>' : (a.key ? '<span class="tlay2-mi-key">' + a.key + '</span>' : '')));
                if (s.disabled) { row.setAttribute('aria-disabled', 'true'); row.classList.add('is-disabled'); }
                row.addEventListener('click', function (ev) {
                    ev.stopPropagation();
                    if (s.disabled) return;
                    if (a.keep) {   // FX strength cycles in place: the menu stays open and shows the new value
                        fire(s, ev);
                        var v = row.querySelector('.tlay2-fxval'); if (v) v.textContent = fxText();
                        return;
                    }
                    closeMenu(false);
                    fire(s, ev);
                });
                menu.appendChild(row); rows.push(row);
            });
        });
        document.body.appendChild(menu);
        // position: right edge on the trigger's right edge, below it; flip above when it would run off the viewport
        var tr = trigger.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
        var mw = menu.offsetWidth, mh = menu.offsetHeight;
        var left = Math.min(Math.max(8, tr.right - mw), Math.max(8, vw - mw - 8));
        var top = tr.bottom + 4;
        if (top + mh > vh - 8) { var above = tr.top - 4 - mh; top = above >= 8 ? above : Math.max(8, vh - 8 - mh); }
        menu.style.left = Math.round(left) + 'px'; menu.style.top = Math.round(top) + 'px';
        menu.style.maxHeight = Math.max(160, vh - 16) + 'px';
        trigger.setAttribute('aria-expanded', 'true');
        var enabled = function () { return rows.filter(function (r) { return r.getAttribute('aria-disabled') !== 'true'; }); };
        var onDown = function (ev) { if (!menu.contains(ev.target) && ev.target !== trigger && !(trigger.contains && trigger.contains(ev.target))) closeMenu(false); };
        var onKey = function (ev) {
            if (!menuState) return;
            if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); closeMenu(true); return; }
            if (ev.key === 'Tab') { closeMenu(false); return; }
            var list = enabled(); if (!list.length) return;
            var cur = list.indexOf(document.activeElement);
            if (ev.key === 'ArrowDown') { ev.preventDefault(); ev.stopPropagation(); list[(cur + 1) % list.length].focus(); }
            else if (ev.key === 'ArrowUp') { ev.preventDefault(); ev.stopPropagation(); list[(cur <= 0 ? list.length : cur) - 1].focus(); }
            else if (ev.key === 'Home') { ev.preventDefault(); list[0].focus(); }
            else if (ev.key === 'End') { ev.preventDefault(); list[list.length - 1].focus(); }
        };
        var onClose = function () { closeMenu(false); };
        var scroller = document.getElementById('layerPanelContent');
        menuState = { menu: menu, trigger: trigger, onDown: onDown, onKey: onKey, onClose: onClose, scroller: scroller };
        document.addEventListener('mousedown', onDown, true);
        document.addEventListener('keydown', onKey, true);
        window.addEventListener('resize', onClose, true);
        if (scroller) scroller.addEventListener('scroll', onClose, true);
        var first = enabled()[0]; if (first) { try { first.focus({ preventScroll: true }); } catch (_e) { first.focus(); } }
    }

    // ------------------------------------------------------------------ the card
    function decorate() {
        var t0 = (typeof performance !== 'undefined') ? performance.now() : 0;
        var panel = document.getElementById('layerPanelContent');
        if (!panel) return;
        var details = panel.querySelector('.layer-row-details');
        closeMenu(false);
        if (!details || details.querySelector(':scope > .tlay2-actions')) return;
        // lift the original buttons out of the card: they keep inline handlers, titles and the disabled state (a locked layer)
        var srcs = {}, groupsEmptied = [], firstGroup = null;
        var kids = details.children;
        for (var i = 0; i < kids.length; i++) {
            var d = kids[i];
            if (d.tagName !== 'DIV') continue;
            var bs = d.querySelectorAll(':scope > .layer-act-btn');
            if (!bs.length) continue;
            for (var j = 0; j < bs.length; j++) {
                var k = keyOf(bs[j]);
                if (!k || srcs[k]) continue;
                var hidden = bs[j].style.display === 'none';   // pc-adjust hides Mirror / Stroke / Export / Make Zone on an adjustment layer
                srcs[k] = bs[j]; bs[j].__t2hidden = hidden;
                if (!firstGroup) firstGroup = d;
            }
        }
        var have = Object.keys(srcs);
        if (!have.length) return;
        // remove the original groups (those whose every .layer-act-btn we lifted); mask / adjustment / group rows (other dataset keys) stay
        var parents = [];
        have.forEach(function (k) { var p = srcs[k].parentNode; if (p && parents.indexOf(p) < 0) parents.push(p); });
        var anchor = firstGroup;
        var holder = document.createDocumentFragment();
        have.forEach(function (k) { if (srcs[k].parentNode) srcs[k].parentNode.removeChild(srcs[k]); holder.appendChild(srcs[k]); });
        var usable = {};
        have.forEach(function (k) { if (!srcs[k].__t2hidden) usable[k] = srcs[k]; });
        var layerId = null;
        try { layerId = (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : window._selectedLayerId; } catch (_e) { }

        var wrap = el('div', 'tlay2-actions', { 'data-tlay2': '1' });
        var bar = el('div', 'tlay2-bar', { role: 'toolbar', 'aria-label': 'Layer Actions' });
        PRIMARY.forEach(function (k) {
            var s = usable[k]; if (!s) return;
            var a = ACT[k];
            var b = el('button', 'tlay2-ib' + (a.danger ? ' tlay2-danger' : ''), { type: 'button', 'data-t2': k, title: s.disabled ? (s.title || a.tip) : a.tip, 'aria-label': a.label }, IC[a.icon]);
            if (s.disabled) { b.disabled = true; b.setAttribute('aria-disabled', 'true'); }
            if (a.toggle) b.setAttribute('aria-pressed', soloOn(layerId) ? 'true' : 'false');
            b.addEventListener('click', function (ev) { ev.stopPropagation(); fire(s, ev); });
            bar.appendChild(b);
        });
        bar.appendChild(el('span', 'tlay2-grow', { 'aria-hidden': 'true' }));
        var more = el('button', 'tlay2-ib tlay2-more', { type: 'button', 'data-t2': 'more', 'aria-haspopup': 'menu', 'aria-expanded': 'false', title: 'More Layer Actions: Arrange, Transform, Effects, Output', 'aria-label': 'More Layer Actions' }, IC.more + '<span class="tlay2-more-lab">More</span>');
        more.addEventListener('click', function (ev) {
            ev.stopPropagation();
            if (menuState && menuState.trigger === more) closeMenu(true); else openMenu(more, usable, layerId);
        });
        more.addEventListener('keydown', function (ev) { if ((ev.key === 'ArrowDown') && !menuState) { ev.preventDefault(); openMenu(more, usable, layerId); } });
        bar.appendChild(more);
        wrap.appendChild(bar);
        wrap.__t2menu = function () { return usable; };

        if (anchor && anchor.parentNode === details) details.insertBefore(wrap, anchor); else details.appendChild(wrap);
        // drop the emptied groups
        parents.forEach(function (p) { if (p.parentNode === details && !p.querySelector('button')) details.removeChild(p); });
        // the old hint line talked about "all layer controls live on this card": say what is true now
        for (var hi = details.children.length - 1; hi >= 0; hi--) {
            var hd = details.children[hi];
            if (hd !== wrap && !hd.firstElementChild && /All layer controls live/.test(hd.textContent || '')) {
                hd.textContent = 'Drag a layer or press Ctrl+[ / ] to reorder';
                hd.classList.add('tlay2-hint');
                break;
            }
        }
        details.setAttribute('data-tlay2-card', '1');
        stats.decorated++;
        if (t0) stats.lastMs = Math.round((performance.now() - t0) * 100) / 100;
    }

    // ------------------------------------------------------------------ hook: after every renderLayerPanel()
    var wrapper = null;
    function hook() {
        var prev = window.renderLayerPanel;
        if (typeof prev !== 'function' || prev.__tlay2) return false;
        var w = function () {
            var r = prev.apply(this, arguments);
            if (w.__dead) return r;
            if (!off()) { try { decorate(); } catch (e) { try { console.warn('[tlay2] card failed', e); } catch (_e) { } } }
            else closeMenu(false);
            return r;
        };
        for (var kp in prev) { try { if (Object.prototype.hasOwnProperty.call(prev, kp) && kp !== '__dead') w[kp] = prev[kp]; } catch (_e2) { } }
        w.__tlay2 = true; w.__dead = false;
        window.renderLayerPanel = w;
        wrapper = w;
        return true;
    }
    function uninstall() { closeMenu(false); if (wrapper) { wrapper.__dead = true; wrapper.__tlay2 = false; } if (iv) clearInterval(iv); }
    hook();
    // a later script may re-wrap renderLayerPanel: keep ours the last wrapper for the first seconds
    // (wrappers copy the own props of what they wrap, so __tlay2 survives a later wrapper; it is only missing when someone REPLACED the function)
    var n = 0, iv = setInterval(function () {
        var cur = window.renderLayerPanel;
        if (typeof cur === 'function' && !cur.__tlay2) hook();
        if (++n >= 20) clearInterval(iv);
    }, 500);
    try { if (typeof renderLayerPanel === 'function' && document.getElementById('layerPanelContent')) renderLayerPanel(); } catch (_e) { }

    window.SPBTlay2Card = { version: 'tlay2-1', uninstall: uninstall, stats: stats, decorate: decorate, closeMenu: closeMenu, ACT: ACT, ICONS: IC, GROUPS: GROUPS, PRIMARY: PRIMARY, off: off };
})();
