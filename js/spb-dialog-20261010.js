/* [SPB-PROMPT-FIX 2026-10-10] js/spb-dialog-20261010.js -- ONE shared in-app dialog module (text box, confirm, pick list).
 *
 * WHY: Electron has no window.prompt() -- it THROWS "prompt() is not supported." (measured in electron-app's Electron 33.4.11,
 * _easy_claude_work/prompt_fix/electron_probe). Every feature that asked for text with prompt() was dead in the shipped app.
 * confirm() / alert() DO work in Electron (native dialogs, input focus intact afterwards), so they stay; SpbDialog.confirm is here
 * for new code and for sites that want the in-app look.
 *
 *   SpbDialog.prompt(title, defaultValue, opts) -> Promise<string|null>      (null = cancelled; '' = OK on an empty box, like prompt())
 *   SpbDialog.confirm(title, opts|message)      -> Promise<boolean>
 *   SpbDialog.choose(title, items, opts)        -> Promise<value|null>       items: [{value,label,sub?}] or plain strings
 *   SpbDialog.isOpen() / SpbDialog.close()      (close = cancel the open one)
 *   SpbDialog.rules.number({min,max,int}) / SpbDialog.rules.hex()  -> validate(value) functions for opts.validate
 *
 * opts: message, hint, placeholder, okLabel, cancelLabel, multiline, rows, maxLength, selectAll(default true), inputMode,
 *       validate(value) -> '' | true (ok)  |  'error text' | false (keeps the dialog open, shows the text), danger (confirm),
 *       nativeText (what the old window.prompt/confirm showed -- used only by the kill switch).
 * The caller keeps its own parsing / range checks after the await (same code as before); validate only saves the user a retry.
 *
 * Keyboard: Enter = OK (Ctrl+Enter in a multi-line box), Esc = Cancel, Tab / Shift+Tab stay inside, arrows move in a pick list.
 * Keys typed in the box never reach the app's tool hotkeys (Photoshop keys, Ctrl+Z). Backdrop clicks do not dismiss (typed text is safe).
 * Dialogs queue one at a time. A request whose title is already open / queued resolves null at once (stops a held Enter key
 * from stacking dialogs and applying a command twice).
 * Kill switch: window.SPB_PROMPT_FIX_OFF = true -> prompt / confirm call the native window.prompt / window.confirm (browser only; a throw resolves null).
 * Styles are injected by this file (no CSS edit needed), so the separate Shokk Drop / Spec Sculpt windows get the same look.
 */
(function () {
    'use strict';
    if (window.SpbDialog) return;

    var CSS = [
        '.spbdlg-back{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;background:rgba(8,9,12,.55);font:400 12px/1.35 var(--pl-font,Inter,"Segoe UI",system-ui,sans-serif);color:var(--pl-tx,#e8e8ea);text-transform:none;letter-spacing:normal;animation:spbdlg-in .09s ease-out}',
        '@keyframes spbdlg-in{from{opacity:0}to{opacity:1}}',
        '@media (prefers-reduced-motion:reduce){.spbdlg-back{animation:none}}',
        '.spbdlg-back .spbdlg{box-sizing:border-box;width:min(400px,100%);max-height:100%;overflow:auto;padding:16px;background:var(--pl-pop,#2a2a30);border:1px solid var(--pl-bd,#3a3a42);border-radius:8px;box-shadow:0 12px 36px rgba(0,0,0,.55);color:var(--pl-tx,#e8e8ea)}',
        '.spbdlg-back .spbdlg-wide{width:min(520px,100%)}',
        '.spbdlg-back .spbdlg-title{margin:0 0 6px;font-size:14px;font-weight:600;line-height:1.25;color:var(--pl-tx,#e8e8ea);text-transform:none;letter-spacing:normal}',
        '.spbdlg-back .spbdlg-msg{margin:0 0 10px;font-size:12px;color:var(--pl-tx2,#c4c4cc);white-space:pre-wrap;word-break:break-word}',
        '.spbdlg-back .spbdlg-hint{margin:6px 0 0;font-size:11px;color:var(--pl-tx3,#9696a1);white-space:pre-wrap}',
        '.spbdlg-back .spbdlg-input{display:block;box-sizing:border-box;width:100%;min-height:32px;margin:0;padding:6px 9px;background:var(--pl-input,#1e1e22);color:var(--pl-tx,#e8e8ea);border:1px solid var(--pl-bd,#3a3a42);border-radius:4px;font:inherit;font-size:13px;text-transform:none;letter-spacing:normal;box-shadow:none;resize:vertical;outline:none}',
        '.spbdlg-back .spbdlg-input:focus{outline:none;border-color:var(--pl-teal,#3fbab5);box-shadow:0 0 0 1px var(--pl-teal,#3fbab5)}',
        '.spbdlg-back .spbdlg-input.spbdlg-bad{border-color:#e5757a;box-shadow:0 0 0 1px #e5757a}',
        '.spbdlg-back .spbdlg-err{min-height:0;margin:6px 0 0;font-size:11px;color:#f08c90}',
        '.spbdlg-back .spbdlg-err:empty{display:none}',
        '.spbdlg-back .spbdlg-list{margin:0;padding:2px;max-height:min(280px,45vh);overflow:auto;background:var(--pl-input,#1e1e22);border:1px solid var(--pl-bd,#3a3a42);border-radius:4px;list-style:none}',
        '.spbdlg-back .spbdlg-list:focus{outline:none;border-color:var(--pl-teal,#3fbab5);box-shadow:0 0 0 1px var(--pl-teal,#3fbab5)}',
        '.spbdlg-back .spbdlg-item{display:flex;align-items:baseline;gap:8px;margin:0;padding:6px 8px;border-radius:3px;cursor:pointer;color:var(--pl-tx,#e8e8ea);font-size:12px;line-height:1.25}',
        '.spbdlg-back .spbdlg-item:hover{background:var(--pl-ctl-h,#38383f)}',
        '.spbdlg-back .spbdlg-item[aria-selected="true"]{background:var(--pl-teal-bg,rgba(63,186,181,.15));box-shadow:inset 0 0 0 1px var(--pl-teal-bd,rgba(63,186,181,.65));color:var(--pl-teal-tx,#8fe0dc)}',
        '.spbdlg-back .spbdlg-sub{margin-left:auto;font-size:11px;color:var(--pl-tx3,#9696a1)}',
        '.spbdlg-back .spbdlg-btns{display:flex;justify-content:flex-end;gap:8px;margin:14px 0 0}',
        '.spbdlg-back .spbdlg-btn{box-sizing:border-box;height:30px;min-width:76px;margin:0;padding:0 14px;background:var(--pl-ctl,#2d2d33);color:var(--pl-tx,#e8e8ea);border:1px solid var(--pl-bd-s,#44444c);border-radius:4px;font:inherit;font-size:12px;font-weight:500;line-height:1;text-transform:none;letter-spacing:normal;cursor:pointer;box-shadow:none}',
        '.spbdlg-back .spbdlg-btn:hover{background:var(--pl-ctl-h,#38383f)}',
        '.spbdlg-back .spbdlg-btn:focus,.spbdlg-back .spbdlg-btn:focus-visible{outline:2px solid var(--pl-teal,#3fbab5);outline-offset:1px}',
        '.spbdlg-back .spbdlg-ok{background:var(--pl-teal-bg,rgba(63,186,181,.15));border-color:var(--pl-teal-bd,rgba(63,186,181,.65));color:var(--pl-teal-tx,#8fe0dc)}',
        '.spbdlg-back .spbdlg-ok:hover{background:rgba(63,186,181,.26)}',
        // [SPB-CONFIRM-POLISH 2026-10-10] a destructive action's OK button is RED-FREE (owner look: no alarm colours): a bright neutral
        // button that NAMES the action ("Delete Zone"), and Cancel holds the focus so a stray Enter cannot delete.
        '.spbdlg-back .spbdlg-danger{background:rgba(255,255,255,.09);border-color:#9a9aa6;color:#f2f2f4}',
        '.spbdlg-back .spbdlg-danger:hover{background:rgba(255,255,255,.17);border-color:#b8b8c2}'
    ].join('\n');

    var cssDone = false;
    function ensureCss() {
        if (cssDone && document.getElementById('spbdlg-css')) return;
        var st = document.createElement('style');
        st.id = 'spbdlg-css';
        st.textContent = CSS;
        (document.head || document.documentElement).appendChild(st);
        cssDone = true;
    }

    function off() { return window.SPB_PROMPT_FIX_OFF === true; }
    function mk(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    var cur = null;     // the open dialog state
    var queue = [];     // waiting requests { key, run }
    var uid = 0;

    function pump() {
        if (cur || !queue.length) return;
        var next = queue.shift();
        next.run();
    }

    function dupKey(key) {
        if (cur && cur.key === key) return true;
        for (var i = 0; i < queue.length; i++) if (queue[i].key === key) return true;
        return false;
    }

    function focusables(root) {
        return Array.prototype.filter.call(root.querySelectorAll('input,textarea,button,[tabindex]'), function (e) {
            return !e.disabled && e.tabIndex >= 0 && e.offsetParent !== null;
        });
    }

    function finish(state, value) {
        if (!state || state.done) return;
        state.done = true;
        if (cur === state) cur = null;
        window.removeEventListener('keydown', state.onKey, true);
        window.removeEventListener('keyup', state.onKeyUp, true);
        window.removeEventListener('keypress', state.onKeyUp, true);
        document.removeEventListener('focusin', state.onFocusIn, true);
        if (state.back.parentNode) state.back.parentNode.removeChild(state.back);
        try {
            var p = state.prevFocus;
            if (p && p.focus && document.contains(p)) p.focus({ preventScroll: true });
        } catch (e) { /* focus is a nicety */ }
        try { state.resolve(value); } catch (e) { /* a caller error must not break the UI */ }
        setTimeout(pump, 0);
    }

    // build + show one dialog.  spec: { key, kind, title, opts, resolve }
    function show(spec) {
        ensureCss();
        var o = spec.opts || {};
        var id = 'spbdlg' + (++uid);
        var back = mk('div', 'spbdlg-back');
        var box = mk('div', 'spbdlg' + (o.multiline || o.wide || spec.kind === 'choose' || (o.message && String(o.message).length > 230) ? ' spbdlg-wide' : ''));
        box.setAttribute('role', 'dialog');
        box.setAttribute('aria-modal', 'true');
        box.setAttribute('aria-labelledby', id + 't');
        var title = mk('div', 'spbdlg-title', spec.title || (spec.kind === 'confirm' ? 'Are You Sure?' : 'Enter A Value'));
        title.id = id + 't';
        box.appendChild(title);
        if (o.message) {
            var msg = mk('div', 'spbdlg-msg', o.message);
            msg.id = id + 'm';
            box.setAttribute('aria-describedby', msg.id);
            box.appendChild(msg);
        }
        var state = { key: spec.key, back: back, box: box, resolve: spec.resolve, prevFocus: document.activeElement, done: false, kind: spec.kind };
        var input = null, list = null, errEl = mk('div', 'spbdlg-err'), selIdx = 0, items = null, firstFocus = null;
        errEl.setAttribute('role', 'alert');

        function currentValue() {
            if (spec.kind === 'prompt') return input.value;
            if (spec.kind === 'choose') return items[selIdx] ? items[selIdx].value : null;
            return true;
        }
        function accept() {
            if (spec.kind === 'prompt' && typeof o.validate === 'function') {
                var r;
                try { r = o.validate(input.value); } catch (e) { r = ''; }
                if (r !== '' && r !== true && r != null) {
                    errEl.textContent = (typeof r === 'string') ? r : 'That value is not valid.';
                    input.classList.add('spbdlg-bad');
                    try { input.focus(); } catch (e) { /* ignore */ }
                    return;
                }
            }
            finish(state, currentValue());
        }
        function cancel() { finish(state, spec.kind === 'confirm' ? false : null); }
        state.cancel = cancel;

        if (spec.kind === 'prompt') {
            input = o.multiline ? mk('textarea', 'spbdlg-input') : mk('input', 'spbdlg-input');
            if (o.multiline) input.rows = o.rows || 5; else input.type = 'text';
            if (o.maxLength) input.maxLength = o.maxLength;
            if (o.placeholder) input.placeholder = o.placeholder;
            if (o.inputMode) input.setAttribute('inputmode', o.inputMode);
            input.value = o.value == null ? '' : String(o.value);
            input.spellcheck = false;
            input.autocomplete = 'off';
            input.setAttribute('aria-label', spec.title || 'Value');
            input.addEventListener('input', function () { errEl.textContent = ''; input.classList.remove('spbdlg-bad'); });
            box.appendChild(input);
            if (o.hint) box.appendChild(mk('div', 'spbdlg-hint', o.hint));
            box.appendChild(errEl);
            firstFocus = input;
        } else if (spec.kind === 'choose') {
            items = spec.items;
            selIdx = Math.max(0, Math.min(items.length - 1, o.selectedIndex | 0));
            list = mk('ul', 'spbdlg-list');
            list.setAttribute('role', 'listbox');
            list.setAttribute('aria-label', spec.title || 'Choices');
            list.tabIndex = 0;
            var rows = items.map(function (it, i) {
                var li = mk('li', 'spbdlg-item');
                li.id = id + 'o' + i;
                li.setAttribute('role', 'option');
                li.appendChild(mk('span', 'spbdlg-lbl', it.label));
                if (it.sub) li.appendChild(mk('span', 'spbdlg-sub', it.sub));
                li.addEventListener('click', function () { setSel(i); });
                li.addEventListener('dblclick', function () { setSel(i); accept(); });
                list.appendChild(li);
                return li;
            });
            var setSel = function (i) {
                if (!rows.length) return;
                selIdx = Math.max(0, Math.min(rows.length - 1, i));
                rows.forEach(function (li, k) { li.setAttribute('aria-selected', k === selIdx ? 'true' : 'false'); });
                list.setAttribute('aria-activedescendant', rows[selIdx].id);
                try { rows[selIdx].scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
            };
            state.setSel = setSel;
            state.getSel = function () { return selIdx; };
            box.appendChild(list);
            if (o.hint) box.appendChild(mk('div', 'spbdlg-hint', o.hint));
            setSel(selIdx);
            firstFocus = list;
        }

        var btns = mk('div', 'spbdlg-btns');
        var cb = mk('button', 'spbdlg-btn spbdlg-cancel', o.cancelLabel || 'Cancel');
        cb.type = 'button';
        cb.addEventListener('click', cancel);
        var ok = mk('button', 'spbdlg-btn spbdlg-ok' + (o.danger ? ' spbdlg-danger' : ''), o.okLabel || 'OK');
        ok.type = 'button';
        ok.addEventListener('click', accept);
        if (!o.single) btns.appendChild(cb);   // [SPB-CONFIRM-POLISH] notice() = one OK button, like alert()
        btns.appendChild(ok);
        box.appendChild(btns);
        if (!firstFocus) firstFocus = (o.danger && !o.single) ? cb : ok; // a destructive confirm focuses Cancel, so a stray Enter cannot delete
        back.appendChild(box);

        // keep every pointer event inside the modal (nothing leaks to canvas tools / outside-click menus)
        ['mousedown', 'pointerdown', 'click', 'dblclick', 'wheel', 'contextmenu'].forEach(function (t) {
            back.addEventListener(t, function (e) {
                e.stopPropagation();
                if (e.target === back && t !== 'wheel') e.preventDefault(); // backdrop: swallow, never dismiss
                // a press on blank dialog area must not pull focus out of the box (typed keys would then miss the input)
                else if (t === 'mousedown' && !/^(INPUT|TEXTAREA|BUTTON|LI|UL|A)$/.test(e.target.tagName)) e.preventDefault();
            });
        });

        state.onKey = function (e) {
            if (!back.contains(e.target) && e.target !== document.body && e.target !== document.documentElement && e.target !== window && e.key !== 'Escape') {
                // focus slipped outside (should not happen): pull it back and swallow
                e.stopPropagation(); e.preventDefault();
                try { firstFocus.focus(); } catch (x) { /* ignore */ }
                return;
            }
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); cancel(); return; }
            if (e.key === 'Tab') {
                e.stopPropagation();
                var f = focusables(box); if (!f.length) { e.preventDefault(); return; }
                var i = f.indexOf(document.activeElement);
                if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
                else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
                return;
            }
            if (e.key === 'Enter' && !e.isComposing) {
                var t = e.target;
                if (t && t.tagName === 'BUTTON') { e.stopPropagation(); return; } // native button activation
                if (t && t.tagName === 'TEXTAREA' && !(e.ctrlKey || e.metaKey)) { e.stopPropagation(); return; } // new line
                e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                accept();
                return;
            }
            if (spec.kind === 'choose' && list && (e.target === list)) {
                var k = e.key, n = items.length, s = state.getSel();
                var ns = k === 'ArrowDown' ? s + 1 : k === 'ArrowUp' ? s - 1 : k === 'Home' ? 0 : k === 'End' ? n - 1 : k === 'PageDown' ? s + 6 : k === 'PageUp' ? s - 6 : null;
                if (ns != null) { e.preventDefault(); e.stopPropagation(); state.setSel(ns); return; }
            }
            // typing in the box: let the browser edit the text, hide the key from app hotkeys
            e.stopPropagation();
        };
        state.onKeyUp = function (e) { if (back.contains(e.target)) e.stopPropagation(); };
        state.onFocusIn = function (e) {
            if (!back.contains(e.target)) { try { firstFocus.focus(); } catch (x) { /* ignore */ } }
        };

        cur = state;
        document.body.appendChild(back);
        window.addEventListener('keydown', state.onKey, true);
        window.addEventListener('keyup', state.onKeyUp, true);
        window.addEventListener('keypress', state.onKeyUp, true);
        document.addEventListener('focusin', state.onFocusIn, true);
        try {
            firstFocus.focus();
            if (input && o.selectAll !== false && !o.readonly) input.select();
        } catch (e) { /* ignore */ }
    }

    function request(kind, title, opts, items, key) {
        return new Promise(function (resolve) {
            var k = key || (kind + ':' + String(title));
            if (dupKey(k)) { resolve(kind === 'confirm' ? false : null); return; }
            var job = { key: k, run: function () { show({ key: k, kind: kind, title: title, opts: opts, items: items, resolve: resolve }); } };
            if (cur) queue.push(job); else job.run();
        });
    }

    function nativeText(title, o) {
        if (o && o.nativeText) return o.nativeText;
        return o && o.message ? (title + '\n\n' + o.message) : String(title == null ? '' : title);
    }

    function prompt(title, defaultValue, opts) {
        var o = {};
        if (title && typeof title === 'object') { o = Object.assign({}, title); title = o.title; defaultValue = o.value; }
        else if (opts && typeof opts === 'object') o = Object.assign({}, opts);
        o.value = defaultValue == null ? '' : defaultValue;
        if (off()) {
            try { var v = window.prompt(nativeText(title, o), o.value); return Promise.resolve(v == null ? null : v); }
            catch (e) { return Promise.resolve(null); }
        }
        return request('prompt', title, o, null, o.key);
    }

    function confirm(title, opts) {
        var o = (typeof opts === 'string') ? { message: opts } : Object.assign({}, opts || {});
        if (title && typeof title === 'object') { o = Object.assign({}, title); title = o.title; }
        if (off()) {
            try { return Promise.resolve(!!window.confirm(nativeText(title, o))); }
            catch (e) { return Promise.resolve(false); }
        }
        return request('confirm', title, o, null, o.key);
    }

    // [SPB-CONFIRM-POLISH 2026-10-10] ask() / notice() -- the in-app replacement for the native confirm() / alert() boxes
    // ("localhost says ..." in the installed app). Kill switch window.SPB_CONFIRM_POLISH_OFF === true: every call goes back to the
    // native box with the OLD text (opts.nativeText).  ask(title, {message, okLabel, cancelLabel, danger, nativeText}) -> Promise<bool>;
    // notice(title, {message, okLabel, nativeText}) -> Promise<void> (one OK button; Enter / Esc / OK all close it).
    // A destructive ask() passes danger:true and an okLabel that names the action ("Delete Zone"); Cancel then holds the focus.
    function polishOff() { return window.SPB_CONFIRM_POLISH_OFF === true; }
    function ask(title, opts) {
        var o = (typeof opts === 'string') ? { message: opts } : Object.assign({}, opts || {});
        if (polishOff()) {
            try { return Promise.resolve(!!window.confirm(nativeText(title, o))); }
            catch (e) { return Promise.resolve(false); }
        }
        return confirm(title, o);
    }
    function notice(title, opts) {
        var o = (typeof opts === 'string') ? { message: opts } : Object.assign({}, opts || {});
        o.single = true;
        if (!o.okLabel) o.okLabel = 'OK';
        if (polishOff() || off()) {
            try { window.alert(nativeText(title, o)); } catch (e) { /* ignore */ }
            return Promise.resolve();
        }
        return request('confirm', title, o, null, o.key || ('notice:' + String(title))).then(function () { return undefined; });
    }

    function choose(title, items, opts) {
        var o = Object.assign({}, opts || {});
        var list = (items || []).map(function (it, i) {
            return (it && typeof it === 'object') ? { value: it.value, label: String(it.label != null ? it.label : it.value), sub: it.sub } : { value: it, label: String(it) };
        });
        if (!list.length) return Promise.resolve(null);
        if (off()) {
            // old behaviour: type the number of the entry
            try {
                var txt = o.nativeText || (title + '\n\n' + list.map(function (it, i) { return (i + 1) + '. ' + it.label; }).join('\n') + '\n\nEnter number:');
                var v = window.prompt(txt);
                if (v == null || v === '') return Promise.resolve(null);
                if (typeof o.nativeResolve === 'function') return Promise.resolve(o.nativeResolve(v, list)); // caller maps the typed text exactly as its old code did
                var n = parseInt(v, 10) - 1;
                return Promise.resolve(list[n] ? list[n].value : null);
            } catch (e) { return Promise.resolve(null); }
        }
        return request('choose', title, o, list, o.key);
    }

    var rules = {
        // number({min,max,int}) -> validate(text). Accepts "40", " 40 ", "-12.5" (int:false). Message names the allowed range.
        number: function (cfg) {
            cfg = cfg || {};
            return function (text) {
                var s = String(text == null ? '' : text).trim();
                var re = cfg.int ? /^[+-]?\d+$/ : /^[+-]?(\d+\.?\d*|\.\d+)$/;
                var range = (cfg.min != null && cfg.max != null) ? ' from ' + cfg.min + ' to ' + cfg.max : '';
                if (!re.test(s)) return 'Enter ' + (cfg.int ? 'a whole number' : 'a number') + range + '.';
                var n = Number(s);
                if ((cfg.min != null && n < cfg.min) || (cfg.max != null && n > cfg.max)) return 'Enter ' + (cfg.int ? 'a whole number' : 'a number') + range + '.';
                return '';
            };
        },
        hex: function () {
            return function (text) { return /^#?[0-9A-Fa-f]{6}$/.test(String(text || '').trim()) ? '' : 'Enter a colour like #FF3366.'; };
        }
    };

    window.SpbDialog = {
        version: 'prompt-fix-1+confirm-polish-1',
        prompt: prompt,
        confirm: confirm,
        ask: ask,
        notice: notice,
        choose: choose,
        rules: rules,
        isOpen: function () { return !!cur; },
        close: function () { if (cur && cur.cancel) cur.cancel(); },
        _queueLength: function () { return queue.length; }
    };
}());
