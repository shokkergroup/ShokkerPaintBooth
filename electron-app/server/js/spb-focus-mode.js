/* ============================================================================
   SPB EASY SHELL controller — Easy is the real Pro workspace, decluttered.
   Owner decision 2026-09-02: the SHOKK DEMO layout is the new Easy Mode model.
   Zones, layers, source paint, previews, renders, and every material slider are
   the SAME live objects as Pro. Switching views never copies or mutates them.

   The historical file/body-class names remain as internal rollback hooks only.
   The persisted value is deliberately `easy-shell`, never `easy`, so the old
   parallel full-screen overlay cannot auto-enter. Saved `easy` and retired
   `focus` installs are migrated synchronously while this script is evaluated —
   before the legacy overlay's delayed boot runs.

   House precedent honored: no ghost shortcut may arm a tool hidden by Easy.
   A capture-phase filter retires hidden tool/edit commands without changing the
   dispatch authority in js/canvas/dispatch.js or either live key router.
   ============================================================================ */
(function () {
    'use strict';

    var LS_MODE = 'spb_view_mode';   // shared with js/spb-easy-mode.js
    var MODE_VALUE = 'easy-shell';
    var BODY_CLASS = 'spb-focus-on';       // internal legacy CSS hook
    var SHELL_CLASS = 'spb-easy-shell-on';
    var BOOT_DELAY_MS = 520;         // land just after Easy Mode's 450ms boot

    var _active = false;
    var _keyFilterInstalled = false;

    function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }

    // Synchronous by design: js/spb-easy-mode.js has already defined its timer,
    // but has not run it yet. Rewriting `easy` now prevents the retired overlay
    // from loading or swapping its isolated Zone project at +450ms.
    function migrateLegacySavedMode() {
        var saved = lsGet(LS_MODE);
        // Owner 2026-09-02: this stripped real-workspace shell is the default
        // first-run experience; an explicit persisted Pro choice still wins.
        // [SPB-EASY-SEPARATE 2026-09-19] owner reversal: EASY is the ISOLATED Easy project again
        // ("EASY MODE should be separate ... they not interfere"). A persisted shell/focus choice
        // migrates to 'easy'; an unset key is left for the first-run card. The shell stays in
        // source as a rollback hook (window.spbEasyShell) and is never auto-entered.
        if (saved === MODE_VALUE || saved === 'focus') lsSet(LS_MODE, 'easy');
    }
    migrateLegacySavedMode();

    // ------------------------------------------------------- keyboard filter
    // Plain-letter keys that arm controls Easy hides. The live eight stay
    // available: P Color, W Wand, L Lasso, O Rect, B Brush, K Fill and E Erase;
    // Exclude has no plain-letter shortcut. The remaining map mirrors both live
    // key routers, including retired/dead routes, so no hidden tool can ghost-arm.
    var BLOCK_PLAIN = {
        a: 1, r: 1, c: 1, q: 1, j: 1, y: 1, v: 1, m: 1, x: 1,
        g: 1, t: 1, u: 1, n: 1, s: 1, i: 1,
        d: 1, f: 1, h: 1, '/': 1, '?': 1
    };
    var ALLOW_SHIFT = { d: 1, n: 1, v: 1 };
    var BLOCK_CTRL = { a: 1, c: 1, d: 1, e: 1, g: 1, i: 1, j: 1, k: 1, l: 1, t: 1, v: 1, x: 1, '/': 1 };

    function isEditableTarget(t) {
        if (!t) return false;
        var tag = (t.tagName || '').toUpperCase();
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
        return !!t.isContentEditable;
    }

    function keyFilter(ev) {
        if (!_active) return;
        if (isEditableTarget(ev.target)) return;
        var k = (ev.key || '').toLowerCase();
        if (ev.key === '?') k = '?';
        var ctrl = ev.ctrlKey || ev.metaKey;
        // Plain tool keys, plus hidden shift-only commands. Keep the useful
        // Zone actions Shift+D/E/N and the visible split-view Shift+V.
        if (!ctrl && !ev.altKey && BLOCK_PLAIN[k] === 1 && !(ev.shiftKey && ALLOW_SHIFT[k] === 1)) {
            ev.stopImmediatePropagation(); ev.preventDefault(); return;
        }
        // Hidden selection, transform, clipboard, fill, script and command-
        // palette routes. Render/save/undo/redo/zoom deliberately stay live.
        if (ctrl && !ev.altKey && BLOCK_CTRL[k] === 1) {
            ev.stopImmediatePropagation(); ev.preventDefault(); return;
        }
        // Backspace fill and plain selection Delete are also invisible tools.
        if ((ev.altKey || ctrl) && ev.key === 'Backspace') {
            ev.stopImmediatePropagation(); ev.preventDefault(); return;
        }
        if (!ctrl && !ev.altKey && !ev.shiftKey && ev.key === 'Delete') {
            ev.stopImmediatePropagation(); ev.preventDefault();
        }
    }

    function installKeyFilter() {
        if (_keyFilterInstalled) return;
        document.addEventListener('keydown', keyFilter, true);
        _keyFilterInstalled = true;
    }

    function uninstallKeyFilter() {
        if (!_keyFilterInstalled) return;
        document.removeEventListener('keydown', keyFilter, true);
        _keyFilterInstalled = false;
    }

    // -------------------------------------------------- exclude-button state
    // setCanvasMode() clears .active on every .vtool-btn then re-adds it to
    // the id in its map — for 'spatial-exclude' that is #vtModeSpatialExclude
    // inside the (hidden) Mask menu. Mirror its class onto the promoted
    // top-level button so the Easy toolbar shows honest tool state.
    function installExcludeMirror() {
        var src = document.getElementById('vtModeSpatialExclude');
        var dst = document.getElementById('vtModeSpatialExcludeTop');
        if (!src || !dst || !window.MutationObserver) return;
        var sync = function () {
            dst.classList.toggle('active', src.classList.contains('active'));
        };
        new MutationObserver(sync).observe(src, { attributes: true, attributeFilter: ['class'] });
        sync();
    }

    // ------------------------------------------------ retired-overlay watch
    // A deep-linked legacy Spec Sculpt can still open the historical overlay.
    // Stand the Easy shell down quietly while that explicit overlay owns view.
    function installEasyWatch() {
        if (!window.MutationObserver) return;
        new MutationObserver(function () {
            if (_active && document.body.classList.contains('spb-easy-on')) {
                standDown();
            }
        }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
    }

    // ------------------------------------------------------------ pill sync
    function syncPillUi() {
        var proBtn = document.getElementById('spbModeProBtn');
        var easyBtn = document.getElementById('spbModeEasyBtn');
        var easyVisible = _active || document.body.classList.contains('spb-easy-on');
        if (easyBtn) {
            easyBtn.classList.toggle('on', easyVisible);
            easyBtn.setAttribute('aria-pressed', easyVisible ? 'true' : 'false');
        }
        if (proBtn) {
            proBtn.classList.toggle('on', !easyVisible);
            proBtn.setAttribute('aria-pressed', easyVisible ? 'false' : 'true');
        }
    }

    // The old first-run chooser is generated inside the retired controller.
    // Keep its one-time lifecycle/cleanup, but route its Easy door to this shell
    // and make the copy truthful about shared Pro state.
    function updateFirstRunCopy() {
        var root = document.getElementById('spbFirstRun');
        if (!root) return;
        var sub = root.querySelector('.spb-fr-sub');
        var door = root.querySelector('#spbFrEasy');
        var foot = root.querySelector('.spb-fr-foot');
        if (sub) sub.innerHTML = 'Both doors use the <b>same live project</b> and the same render engine. Switch any time with <b>PRO&nbsp;|&nbsp;EASY</b>; your Zones and Layers stay exactly where they are.';
        if (door) {
            var badge = door.querySelector('.spb-fr-badge');
            var desc = door.querySelector('p');
            var list = door.querySelector('ul');
            if (badge) badge.textContent = 'SIMPLIFIED · SWITCH ANY TIME';
            if (desc) desc.textContent = 'The real Paint Booth with the advanced controls tucked away.';
            if (list) list.innerHTML = '<li>Real Zones, Layers, previews and rendering</li><li>Every Base Material and Base Color control</li><li>Color, Exclude, Wand, Lasso, Rect, Brush, Fill and Erase</li>';
        }
        if (foot) foot.innerHTML = 'New to the booth? Start in <b>EASY</b>. Ready for every pattern and editing tool? Switch to <b>PRO</b> without losing your place.';
    }

    function firstRunEasyRoute(ev) {
        var target = ev.target && ev.target.closest ? ev.target.closest('#spbFrEasy') : null;
        if (!target) return;
        ev.preventDefault();
        ev.stopImmediatePropagation();
        // Let the retired chooser's Pro handler remove its dialog and key trap,
        // then enter the new shared-state Easy shell.
        var proDoor = document.getElementById('spbFrPro');
        if (proDoor) proDoor.click();
        else {
            var root = document.getElementById('spbFirstRun');
            if (root && root.parentNode) root.parentNode.removeChild(root);
            document.body.classList.remove('spb-firstrun-open');
        }
        enter();
    }

    function installFirstRunBridge() {
        return;   // [SPB-EASY-SEPARATE 2026-09-19] the first-run EASY door belongs to the isolated Easy again
        document.addEventListener('click', firstRunEasyRoute, true);
        updateFirstRunCopy();
        if (!window.MutationObserver || !document.body) return;
        new MutationObserver(updateFirstRunCopy).observe(document.body, { childList: true });
    }

    // -------------------------------------------------------- enter / exit
    function enter() {
        // The retired controller boots 70 ms earlier and still syncs the same
        // header pill. Reassert our truthful state if Easy was clicked during
        // that narrow startup window instead of returning with PRO highlighted.
        if (_active) {
            syncPillUi();
            return;
        }
        if (document.body.classList.contains('spb-easy-on')) {
            try { if (window.spbEasy) window.spbEasy.exit(); } catch (e) { }
        }
        document.body.classList.add(BODY_CLASS);
        document.body.classList.add(SHELL_CLASS);
        _active = true;
        lsSet(LS_MODE, MODE_VALUE);
        installKeyFilter();
        // Land on the owner's workflow: zone editing, Color armed, and
        // (once paint is loaded) the SOURCE + LIVE PREVIEW split the mode
        // promises — the SOURCE/CAR/SPLIT toggle is hidden here.
        try { if (typeof window.setToolbarEditMode === 'function') window.setToolbarEditMode('zone'); } catch (e) { }
        try { if (typeof window.setCanvasMode === 'function') window.setCanvasMode('eyedropper'); } catch (e) { }
        try {
            var loaded = document.getElementById('paintPreviewLoaded');
            if (loaded && window.getComputedStyle(loaded).display !== 'none' &&
                typeof window.setCanvasDisplayMode === 'function') {
                window.setCanvasDisplayMode('split');
            }
        } catch (e) { }
        syncPillUi();
    }

    function exit() {
        // A fast click before delayed boot must cancel a persisted Easy entry.
        if (!_active) {
            if (lsGet(LS_MODE) === MODE_VALUE) lsSet(LS_MODE, 'pro');
            syncPillUi();
            return;
        }
        document.body.classList.remove(BODY_CLASS);
        document.body.classList.remove(SHELL_CLASS);
        _active = false;
        if (lsGet(LS_MODE) === MODE_VALUE) lsSet(LS_MODE, 'pro');
        uninstallKeyFilter();
        syncPillUi();
    }

    // Easy Mode took over: drop the class + filter but leave spb_view_mode to
    // Easy (its exit() writes 'pro').
    function standDown() {
        document.body.classList.remove(BODY_CLASS);
        document.body.classList.remove(SHELL_CLASS);
        _active = false;
        uninstallKeyFilter();
        syncPillUi();
    }

    // --------------------------------------------------------------- boot
    function boot() {
        installExcludeMirror();
        installEasyWatch();
        // [SPB-EASY-SEPARATE 2026-09-19] the first-run card describes the isolated Easy again; the shell copy rewrite is retired
        if (lsGet(LS_MODE) === MODE_VALUE) enter();
        else syncPillUi();
    }

    installFirstRunBridge();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, BOOT_DELAY_MS); });
    } else {
        setTimeout(boot, BOOT_DELAY_MS);
    }

    var api = {
        enter: enter,
        exit: exit,
        isActive: function () { return _active; }
    };
    window.spbEasyShell = api;
    window.spbFocus = api; // internal backwards-compatible rollback alias
})();
