/* SPB-93 2026-09-07: retain transform controls through typing and focus transfer.
   Rebuilding on input blur detached the next Tab/click target. Refresh after
   focus leaves the options bar; Apply/Cancel still retire controls immediately. */
(function (root) {
    'use strict';
    const pending = new WeakMap();
    function discard(container) {
        const state = pending.get(container);
        if (!state) return;
        container.removeEventListener('focusout', state.onFocusOut);
        pending.delete(container);
    }
    function syncControls(container, markup, active) {
        // Keep control nodes/focus stable while reflecting commands such as Reset.
        const template = root.document.createElement('template');
        template.innerHTML = markup;
        const selector = 'button, input, select';
        const existing = container.querySelectorAll(selector);
        const incoming = template.content.querySelectorAll(selector);
        if (existing.length !== incoming.length) return;
        for (let i = 0; i < existing.length; i++) {
            const current = existing[i], next = incoming[i];
            if (current.tagName !== next.tagName) continue;
            current.className = next.className;
            current.disabled = next.disabled;
            if (current.tagName === 'BUTTON') {
                // Preserve the focused node while Set/Clear isolation changes its action.
                for (const name of ['onclick', 'title', 'aria-label', 'aria-pressed']) {
                    const value = next.getAttribute(name);
                    if (value === null) current.removeAttribute(name);
                    else current.setAttribute(name, value);
                }
                if (current.innerHTML !== next.innerHTML) current.innerHTML = next.innerHTML;
            }
            if (current !== active && current.hasAttribute('data-transform-field')) {
                current.value = next.value;
            }
        }
    }
    function setMarkup(container, markup, refresh, preserveFocused = true) {
        const active = root.document?.activeElement;
        if (preserveFocused && active && container.contains(active) &&
            (pending.has(container) || active.hasAttribute?.('data-transform-field'))) {
            let state = pending.get(container);
            if (!state) {
                state = { refresh, queued: false };
                state.onFocusOut = () => {
                    if (state.queued) return;
                    state.queued = true;
                    (root.requestAnimationFrame || (fn => fn()))(() => {
                        state.queued = false;
                        if (pending.get(container) !== state) return;
                        if (container.contains(root.document?.activeElement)) return;
                        const latest = state.refresh;
                        discard(container);
                        if (typeof latest === 'function') latest();
                    });
                };
                pending.set(container, state);
                container.addEventListener('focusout', state.onFocusOut);
            }
            syncControls(container, markup, active);
            state.refresh = refresh;
            return false;
        }
        discard(container);
        container.innerHTML = markup;
        return true;
    }
    const api = { setMarkup };
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SPBToolOptionsFocus = api;
})(typeof window === 'object' ? window : globalThis);
