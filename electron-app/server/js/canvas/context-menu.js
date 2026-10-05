/* SPB-93: keep all existing canvas commands reachable in a bounded menu. */
(function() {
    'use strict';
    let closeActive = null;
    window.SPBCanvasContextMenu = { open(event, items, run) {
        if (closeActive) closeActive();
        const menu = document.createElement('div');
        menu.id = 'canvasContextMenu';
        menu.setAttribute('role', 'menu');
        menu.setAttribute('aria-label', 'Canvas actions');
        menu.style.cssText = 'position:fixed;z-index:100000;background:#1a1a2e;border:1px solid #00e5ff;border-radius:6px;padding:4px 0;min-width:160px;max-width:calc(100vw - 16px);max-height:calc(100vh - 16px);overflow-y:auto;box-shadow:0 4px 16px #0008;font-size:11px;';
        const opener = document.activeElement;
        function close(restoreFocus) {
            menu.remove();
            document.removeEventListener('pointerdown', outside, true);
            if (closeActive === close) closeActive = null;
            if (restoreFocus && opener?.isConnected) opener.focus({preventScroll:true});
        }
        function outside(e) { if (!menu.contains(e.target)) close(false); }
        closeActive = close;
        for (const item of items) {
            if (item.sep) {
                const line = document.createElement('div');
                line.setAttribute('role', 'separator');
                line.style.cssText = 'border-top:1px solid #333;margin:2px 0';
                menu.appendChild(line); continue;
            }
            const button = document.createElement('button');
            button.type = 'button'; button.className = '_ctx_item';
            button.setAttribute('role', 'menuitem');
            button.setAttribute('data-fn', item.fn);
            button.style.cssText = 'width:100%;text-align:left;border:0;background:transparent;font:inherit;padding:5px 12px;cursor:pointer;display:flex;justify-content:space-between;gap:16px;color:#ddd';
            const label = document.createElement('span'), key = document.createElement('span');
            label.textContent = item.l; key.textContent = item.k || '';
            key.style.cssText = 'color:#888;font-size:9px';
            button.append(label, key);
            button.addEventListener('pointerenter', () => {button.style.background='rgba(0,229,255,.1)';});
            button.addEventListener('pointerleave', () => {button.style.background='transparent';});
            button.addEventListener('click', () => { close(false); run(item.fn); });
            menu.appendChild(button);
        }
        document.body.appendChild(menu);
        const rect = menu.getBoundingClientRect();
        menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth-rect.width-8))+'px';
        menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight-rect.height-8))+'px';
        menu.addEventListener('keydown', e => {
            // Menu keys belong to the menu, never the transform underneath.
            e.stopPropagation();
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault(); document.activeElement?.click(); return;
            }
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(true); return; }
            if (!['ArrowDown','ArrowUp','Home','End'].includes(e.key)) return;
            e.preventDefault(); e.stopPropagation();
            const buttons = Array.from(menu.querySelectorAll('button'));
            let index = buttons.indexOf(document.activeElement);
            index = e.key === 'Home' ? 0 : e.key === 'End' ? buttons.length-1
                : (index+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length;
            buttons[index]?.focus();
        });
        document.addEventListener('pointerdown', outside, true);
        menu.querySelector('button')?.focus({preventScroll:true});
        return menu;
    }};
}());
