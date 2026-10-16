/* [SPB-TLAY2 2026-10-10] L2-2 -- in-app text / colour-tag popovers for the layer panel.
 *
 * WHY: Electron has no window.prompt() (it throws "prompt() is and will not be supported"), so every layer command that used it
 * (dock rename, context-menu Rename / Add comment / Color tag, effect-preset name, effects JSON import / export) silently did
 * nothing in the packaged app. This file gives them real, anchored, keyboard-driven popovers.
 *
 *   SPBTlay2Ui.prompt({ title, value, placeholder, hint, multiline, rows, maxLength, okLabel, cancelLabel, readonly, anchor }) -> Promise<string|null>
 *   SPBTlay2Ui.colorTag({ value, anchor, title }) -> Promise<'red'|'orange'|...|'none'|null>
 *
 * anchor = an Element, or {x, y}. Esc / outside click / Cancel resolve null. Enter confirms (Ctrl+Enter for multi-line).
 * Kill switch: window.SPB_TLAY2_OFF = true -> callers fall back to window.prompt (which only works in a browser).
 * Styles live in css/spb-clean-default-20260829.css ([SPB-TLAY2] block, .tlay2-pop*).
 */
(function () {
    'use strict';
    if (window.SPBTlay2Ui) return;

    var cur = null; // { pop, resolve, onDown, onKey, onResize, prevFocus }

    var TAGS = [
        ['red', 'Red', '#ff5a5a'], ['orange', 'Orange', '#ff9a4a'], ['yellow', 'Yellow', '#ffd700'], ['green', 'Green', '#5eead4'],
        ['blue', 'Blue', '#60a5fa'], ['purple', 'Purple', '#c084fc'], ['gray', 'Gray', '#94a3b8'], ['none', 'None', '']
    ];

    function mk(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    function close(val) {
        var c = cur;
        if (!c) return;
        cur = null;
        document.removeEventListener('mousedown', c.onDown, true);
        document.removeEventListener('keydown', c.onKey, true);
        window.removeEventListener('resize', c.onResize, true);
        if (c.pop.parentNode) c.pop.parentNode.removeChild(c.pop);
        try { if (c.prevFocus && c.prevFocus.focus && document.contains(c.prevFocus)) c.prevFocus.focus(); } catch (e) { /* focus is a nicety */ }
        try { c.resolve(val === undefined ? null : val); } catch (e) { /* caller error must not break the UI */ }
    }

    function place(pop, anchor) {
        var vw = window.innerWidth, vh = window.innerHeight, r;
        var b0 = anchor && anchor.getBoundingClientRect ? anchor.getBoundingClientRect() : null;
        if (b0 && (b0.width > 0 || b0.height > 0)) r = { left: b0.left, top: b0.top, bottom: b0.bottom, right: b0.right }; // a hidden anchor (display:none dock) has a 0x0 rect -> centre instead
        else if (b0) r = null;
        else if (anchor && typeof anchor.x === 'number') r = { left: anchor.x, top: anchor.y, bottom: anchor.y, right: anchor.x };
        if (!r) r = { left: vw / 2 - 140, top: vh / 3, bottom: vh / 3, right: vw / 2 + 140 };
        var pw = pop.offsetWidth, ph = pop.offsetHeight;
        var x = Math.min(Math.max(8, r.left), Math.max(8, vw - pw - 8));
        var y = r.bottom + 6;
        if (y + ph > vh - 8) y = Math.max(8, r.top - ph - 6);
        if (y + ph > vh - 8) y = Math.max(8, vh - ph - 8);
        pop.style.left = Math.round(x) + 'px';
        pop.style.top = Math.round(y) + 'px';
    }

    function focusables(pop) {
        return Array.prototype.filter.call(pop.querySelectorAll('input,textarea,button,[tabindex]'), function (e) { return !e.disabled && e.tabIndex >= 0 && e.offsetParent !== null; });
    }

    function open(build, anchor, label, onKeyExtra) {
        if (cur) close(null);
        return new Promise(function (resolve) {
            var pop = mk('div', 'tlay2-pop');
            pop.setAttribute('role', 'dialog');
            pop.setAttribute('aria-label', label || 'Layer');
            pop.style.visibility = 'hidden';
            var state = { pop: pop, resolve: resolve, prevFocus: document.activeElement };
            var first = build(pop, function (v) { close(v); });
            document.body.appendChild(pop);
            place(pop, anchor);
            pop.style.visibility = '';
            state.onDown = function (e) { if (!pop.contains(e.target)) close(null); };
            state.onKey = function (e) {
                if (!pop.contains(document.activeElement) && e.key !== 'Escape') return;
                if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(null); return; }
                if (e.key === 'Tab') {
                    var f = focusables(pop); if (!f.length) return;
                    var i = f.indexOf(document.activeElement);
                    if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
                    else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
                    return;
                }
                if (onKeyExtra) onKeyExtra(e);
            };
            state.onResize = function () { place(pop, anchor); };
            document.addEventListener('mousedown', state.onDown, true);
            document.addEventListener('keydown', state.onKey, true);
            window.addEventListener('resize', state.onResize, true);
            cur = state;
            try { if (first) first.focus(); } catch (e) { /* ignore */ }
        });
    }

    function prompt(o) {
        o = o || {};
        var multi = !!o.multiline;
        var input;
        function done(v) { close(v); }
        return open(function (pop, finish) {
            pop.classList.add(multi ? 'tlay2-pop-wide' : 'tlay2-pop-narrow');
            pop.appendChild(mk('div', 'tlay2-pop-title', o.title || 'Enter A Value'));
            if (o.hint) pop.appendChild(mk('div', 'tlay2-pop-hint', o.hint));
            input = multi ? mk('textarea', 'tlay2-pop-input') : mk('input', 'tlay2-pop-input');
            if (multi) input.rows = o.rows || 5; else input.type = 'text';
            if (o.maxLength) input.maxLength = o.maxLength;
            if (o.placeholder) input.placeholder = o.placeholder;
            if (o.readonly) input.readOnly = true;
            input.value = o.value == null ? '' : String(o.value);
            input.setAttribute('aria-label', o.title || 'Value');
            input.spellcheck = false;
            pop.appendChild(input);
            var row = mk('div', 'tlay2-pop-btns');
            if (!o.noCancel) {
                var cb = mk('button', 'tlay2-pop-btn', o.cancelLabel || 'Cancel'); cb.type = 'button';
                cb.addEventListener('click', function () { finish(null); });
                row.appendChild(cb);
            }
            var ok = mk('button', 'tlay2-pop-btn tlay2-pop-ok', o.okLabel || 'OK'); ok.type = 'button';
            ok.addEventListener('click', function () { finish(o.readonly ? null : input.value); });
            row.appendChild(ok);
            pop.appendChild(row);
            // select the text so typing replaces it (rename / paste flows)
            setTimeout(function () { try { input.focus(); if (o.selectAll !== false) input.select(); } catch (e) { /* ignore */ } }, 0);
            return input;
        }, o.anchor, o.title, function (e) {
            if (e.key !== 'Enter' || e.target !== input) return;
            if (multi && !(e.ctrlKey || e.metaKey)) return; // plain Enter = new line in a multi-line box
            e.preventDefault(); e.stopPropagation();
            close(o.readonly ? null : input.value);
        });
    }

    function colorTag(o) {
        o = o || {};
        var cur0 = String(o.value || 'none').toLowerCase();
        var btns = [];
        return open(function (pop, finish) {
            pop.classList.add('tlay2-pop-narrow');
            pop.appendChild(mk('div', 'tlay2-pop-title', o.title || 'Color Tag'));
            var row = mk('div', 'tlay2-swatches');
            row.setAttribute('role', 'radiogroup');
            TAGS.forEach(function (t) {
                var b = mk('button', 'tlay2-swatch' + (t[0] === 'none' ? ' tlay2-swatch-none' : ''));
                b.type = 'button'; b.title = t[1]; b.setAttribute('aria-label', t[1]);
                b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', t[0] === cur0 ? 'true' : 'false');
                b.dataset.tag = t[0];
                if (t[2]) b.style.setProperty('--sw', t[2]);
                b.addEventListener('click', function () { finish(t[0]); });
                row.appendChild(b); btns.push(b);
            });
            pop.appendChild(row);
            var hit = btns.filter(function (b) { return b.dataset.tag === cur0; })[0] || btns[btns.length - 1];
            return hit;
        }, o.anchor, o.title || 'Color tag', function (e) {
            var i = btns.indexOf(document.activeElement);
            if (i < 0) return;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); btns[(i + 1) % btns.length].focus(); }
            else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); btns[(i + btns.length - 1) % btns.length].focus(); }
        });
    }

    window.SPBTlay2Ui = { version: 'tlay2-2', prompt: prompt, colorTag: colorTag, close: function () { close(null); }, isOpen: function () { return !!cur; }, TAGS: TAGS };
})();
