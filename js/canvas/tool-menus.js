/* SPB-93 2026-09-07 — owner: familiar, responsive tools without lost options.
 * Menu navigation owns its keys; Escape in a menu must not cancel canvas work.
 * Tool actions themselves remain on their existing buttons/dispatch paths.
 */
(function () {
    'use strict';
    const bar = document.getElementById('spbTopToolbar');
    if (!bar) return;
    const selector = 'details.spb-tb-menu';
    function closeMenus(except) {
        bar.querySelectorAll(selector + '[open]').forEach(menu => {
            if (menu !== except) menu.open = false;
        });
    }
    function fitMenu(menu) {
        const pop = menu.querySelector('.spb-tb-pop');
        if (!pop || !menu.open) return;
        pop.style.removeProperty('transform');
        const rect = pop.getBoundingClientRect();
        const shift = Math.max(8 - rect.left, Math.min(0, window.innerWidth - 8 - rect.right));
        pop.style.transform = 'translateX(' + shift + 'px)';
        pop.style.maxHeight = Math.max(80, window.innerHeight - rect.top - 8) + 'px';
    }
    bar.addEventListener('toggle', event => {
        const menu = event.target;
        if (!menu.matches || !menu.matches(selector) || !menu.open) return;
        closeMenus(menu);
        fitMenu(menu);
    }, true);
    bar.addEventListener('click', event => {
        const button = event.target.closest('.spb-tb-pop .vtool-btn');
        if (button) button.closest(selector).open = false;
    });
    document.addEventListener('click', event => {
        if (!bar.contains(event.target)) closeMenus();
    });
    document.addEventListener('keydown', event => {
        const open = bar.querySelector(selector + '[open]');
        if (event.key === 'Escape' && open) {
            event.preventDefault();
            event.stopImmediatePropagation();
            closeMenus();
            open.querySelector('summary').focus({preventScroll:true});
            return;
        }
        const menu = event.target.closest && event.target.closest(selector);
        if (!menu || !bar.contains(menu) || event.altKey || event.ctrlKey || event.metaKey) return;
        if (event.target.matches('input, select, textarea, [contenteditable="true"]')) return;
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        menu.open = true;
        closeMenus(menu);
        fitMenu(menu);
        const buttons = [...menu.querySelectorAll('.spb-tb-pop button:not(:disabled)')]
            .filter(button => button.getClientRects().length && getComputedStyle(button).visibility !== 'hidden');
        if (!buttons.length) return;
        const index = buttons.indexOf(document.activeElement);
        let next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
            : event.key === 'ArrowDown' ? (index + 1) % buttons.length
            : index < 0 ? buttons.length - 1 : (index + buttons.length - 1) % buttons.length;
        buttons[next].focus({preventScroll:true});
        buttons[next].scrollIntoView({block:'nearest', inline:'nearest'});
    }, true);
    window.addEventListener('resize', () => {
        bar.querySelectorAll(selector + '[open]').forEach(fitMenu);
    });
}());
