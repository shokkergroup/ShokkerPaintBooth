(function (root, factory) {
    const api = factory(root || {});
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    if (root) root.SPBCanvasConfirmDialog = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';

    let active = null;

    function close(reason) {
        if (!active) return false;
        const current = active;
        active = null;
        try { root.document.removeEventListener('keydown', current.onKeyDown, true); } catch (_) {}
        try { current.overlay.remove(); } catch (_) {}
        if (reason === 'confirm' && typeof current.onConfirm === 'function') current.onConfirm();
        if (reason !== 'confirm' && typeof current.onCancel === 'function') current.onCancel();
        return true;
    }

    function open(options) {
        const doc = root.document;
        if (!doc || !doc.body) return false;
        if (active) close('replaced');
        const opts = options || {};

        const overlay = doc.createElement('div');
        overlay.className = 'spb-canvas-confirm-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:26000;background:rgba(0,0,0,.04);';

        const panel = doc.createElement('section');
        panel.className = 'spb-canvas-confirm-panel';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-modal', 'true');
        panel.setAttribute('aria-labelledby', 'spbCanvasConfirmTitle');
        panel.style.cssText = 'position:absolute;left:12px;top:50%;transform:translateY(-50%);width:min(370px,calc(100vw - 24px));max-height:calc(100vh - 24px);overflow:auto;box-sizing:border-box;padding:16px;border:1px solid rgba(255,173,51,.75);border-radius:12px;background:#0d1420;color:#e9f1ff;box-shadow:0 18px 55px rgba(0,0,0,.72);font:12px/1.45 system-ui,sans-serif;';

        const title = doc.createElement('h2');
        title.id = 'spbCanvasConfirmTitle';
        title.textContent = opts.title || 'Confirm';
        title.style.cssText = 'margin:0 0 8px;color:#ffbd59;font-size:16px;line-height:1.2;';
        panel.appendChild(title);

        const message = doc.createElement('div');
        message.textContent = opts.message || '';
        message.style.cssText = 'white-space:pre-wrap;color:#d6e2f2;';
        panel.appendChild(message);

        if (Array.isArray(opts.details) && opts.details.length) {
            const list = doc.createElement('ul');
            list.style.cssText = 'margin:10px 0 0;padding-left:20px;color:#ffcf85;';
            opts.details.forEach(function (detail) {
                const item = doc.createElement('li');
                item.textContent = String(detail);
                item.style.marginBottom = '5px';
                list.appendChild(item);
            });
            panel.appendChild(list);
        }

        const actions = doc.createElement('div');
        actions.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;margin-top:16px;';
        const cancel = doc.createElement('button');
        cancel.type = 'button';
        cancel.textContent = opts.cancelLabel || 'Cancel';
        cancel.style.cssText = 'min-width:88px;padding:8px 12px;border:1px solid #405268;border-radius:7px;background:#162234;color:#dce8f8;cursor:pointer;font-weight:700;';
        const confirm = doc.createElement('button');
        confirm.type = 'button';
        confirm.textContent = opts.confirmLabel || 'Continue';
        confirm.style.cssText = 'min-width:112px;padding:8px 12px;border:1px solid #ff9f2f;border-radius:7px;background:#7a2f18;color:#fff4e6;cursor:pointer;font-weight:900;';
        actions.append(cancel, confirm);
        panel.appendChild(actions);
        overlay.appendChild(panel);
        doc.body.appendChild(overlay);

        const onKeyDown = function (event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                event.stopPropagation();
                close('cancel');
            }
        };
        active = { overlay, onKeyDown, onConfirm: opts.onConfirm, onCancel: opts.onCancel };
        doc.addEventListener('keydown', onKeyDown, true);
        cancel.addEventListener('click', function () { close('cancel'); });
        confirm.addEventListener('click', function () { close('confirm'); });
        overlay.addEventListener('click', function (event) {
            if (event.target === overlay) close('cancel');
        });
        cancel.focus();
        return true;
    }

    return { open, close };
});
