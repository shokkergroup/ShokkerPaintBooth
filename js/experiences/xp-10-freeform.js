/* ============================================================================
 * EXPERIENCE 10 — FREEFORM
 * Paradigm: SPATIAL / USER-ARRANGED. You decide where the panels live.
 *
 * Every other experience makes the arrangement decision for you. Freeform hands
 * it over: each rail gets a DOCK CHOOSER (left / right / hidden), and the choice
 * persists. Two painters who work differently stop fighting one layout.
 *
 * It is genuinely spatial but deliberately NOT free-floating drag-anywhere —
 * dragging panels over the canvas would break the owner's rule that SOURCE and
 * LIVE PREVIEW are never covered. Docking to an edge rearranges the flex row, so
 * the artwork simply takes whatever is left and can never be sat on.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '10-freeform',
        name: 'Freeform',
        tagline: 'Send any rail left, right, or away. Your bench, your call.',
        paradigm: 'User-arranged docking',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            var main = ctx.q('.main-container');
            var left = ctx.q('#leftPanel');
            var right = ctx.q('#rightPanel');
            var center = ctx.q('#centerPanel');
            if (!main || !left || !right || !center) return;

            var KEY = 'shokker_xp_freeform_docks';
            // Default MIRRORED (zones right, finishes left). The point of this
            // experience is that the arrangement is yours — a mirrored default
            // shows that the instant it loads, instead of looking identical to
            // every other pack until you click something.
            // Default: BOTH rails on the right, artwork hard left — the exact
            // mirror of Studio, and the clearest possible demonstration of what
            // this pack is for. One click on any dock button proves the point.
            var state = { zones: 'right', finishes: 'right' };
            try { state = Object.assign(state, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (_) {}

            var PANELS = [
                { key: 'zones', el: left, label: 'ZONES' },
                { key: 'finishes', el: right, label: 'FINISHES + LAYERS' }
            ];

            function place() {
                PANELS.forEach(function (p) {
                    var side = state[p.key];
                    p.el.classList.toggle('xp-ff-away', side === 'away');
                    if (side === 'away') return;
                    // Re-order within .main-container: left rails before the
                    // center column, right rails after it. Pure flex order — the
                    // artwork keeps whatever width is left and is never overlaid.
                    if (side === 'left') main.insertBefore(p.el, center);
                    else main.appendChild(p.el);
                });
                try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (_) {}
                ctx.refit();
            }

            // Each panel gets a small chooser pinned to its own header.
            PANELS.forEach(function (p) {
                var bar = ctx.mk('div', { cls: 'xp-ff-dockbar' });
                ['left', 'right', 'away'].forEach(function (side) {
                    var b = ctx.mk('button', {
                        cls: 'xp-ff-dockbtn',
                        attrs: { type: 'button', 'data-side': side,
                                 title: p.label + ' → ' + side,
                                 'aria-label': p.label + ' dock ' + side },
                        text: side === 'left' ? '◧' : (side === 'right' ? '◨' : '✕')
                    });
                    ctx.on(b, 'click', function () {
                        state[p.key] = side;
                        place();
                        sync();
                    });
                    bar.appendChild(b);
                });
                p.el.insertBefore(bar, p.el.firstChild);
                ctx.onTeardown(function () { if (bar.parentNode) bar.parentNode.removeChild(bar); });
                p._bar = bar;
            });

            function sync() {
                PANELS.forEach(function (p) {
                    p._bar.querySelectorAll('.xp-ff-dockbtn').forEach(function (b) {
                        b.classList.toggle('on', b.getAttribute('data-side') === state[p.key]);
                    });
                });
            }

            // A panel sent away leaves a permanent bring-it-back chip, so
            // "away" can never become "gone".
            var tray = ctx.mk('div', { cls: 'xp-ff-tray', into: '#centerPanel' });
            PANELS.forEach(function (p) {
                var chip = ctx.mk('button', {
                    cls: 'xp-ff-chip', text: '⟵ ' + p.label,
                    attrs: { type: 'button' }
                });
                ctx.on(chip, 'click', function () {
                    state[p.key] = (p.key === 'zones' ? 'left' : 'right');
                    place(); sync(); paintTray();
                });
                tray.appendChild(chip);
                p._chip = chip;
            });
            function paintTray() {
                var any = false;
                PANELS.forEach(function (p) {
                    var away = state[p.key] === 'away';
                    p._chip.style.display = away ? '' : 'none';
                    if (away) any = true;
                });
                tray.style.display = any ? '' : 'none';
            }

            place(); sync(); paintTray();
            var _oldPaint = paintTray;
            PANELS.forEach(function (p) {
                p._bar.addEventListener('click', function () { setTimeout(_oldPaint, 0); });
            });
            ctx.onTeardown(function () {
                // Put the rails back in Classic order regardless of the saved layout.
                main.insertBefore(left, center);
                main.appendChild(right);
                left.classList.remove('xp-ff-away');
                right.classList.remove('xp-ff-away');
            });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:10px; --ff-a:#a3e635; }',
                '& #splitViewContainer{ padding:8px !important; gap:8px; }',
                '& .main-container, & #centerPanel{ background:#101410 !important; }',
                '& .header, & #spbTopToolbar{ background:#141a13 !important;',
                '  border-bottom:1px solid #26301f !important; }',
                '& .left-panel, & .right-panel{ background:#141a13 !important;',
                '  border-color:#26301f !important; position:relative !important; }',
                '& .xp-ff-away{ display:none !important; }',

                '& .xp-ff-dockbar{ display:flex; gap:3px; padding:4px 5px; flex:0 0 auto;',
                '  background:#0e1310; border-bottom:1px solid #26301f; }',
                '& .xp-ff-dockbtn{ flex:1 1 0; padding:3px 0; cursor:pointer; font-size:11px;',
                '  background:transparent; color:#6f8360; border:1px solid #26301f; border-radius:5px; }',
                '& .xp-ff-dockbtn:hover{ color:#cfe6b8; border-color:#3f5233; }',
                '& .xp-ff-dockbtn.on{ background:rgba(163,230,53,0.16); color:var(--ff-a);',
                '  border-color:var(--ff-a); }',

                '& .xp-ff-tray{ position:absolute; left:12px; bottom:10px; z-index:70;',
                '  display:flex; gap:6px; }',
                '& .xp-ff-chip{ padding:6px 12px; border-radius:999px; cursor:pointer;',
                '  background:rgba(163,230,53,0.14); color:var(--ff-a);',
                '  border:1px solid var(--ff-a); font-size:11px; font-weight:700; }',

                '& #splitSource, & #splitPreview{ background:#070a06 !important;',
                '  border:1px solid #26301f !important; border-radius:10px !important;',
                '  box-shadow:0 14px 34px rgba(0,0,0,0.5) !important; }',
                '& #previewTopStrip{ flex:0 0 auto !important; padding:5px 10px !important;',
                '  min-height:0 !important; background:#141a13 !important;',
                '  border:1px solid #26301f !important; border-radius:9px !important; gap:10px !important; }',
                '& #previewTopStrip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:9px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:var(--ff-a) !important; color:#101410 !important;',
                '  border:none !important; border-radius:9px !important; font-weight:800 !important;',
                '  letter-spacing:1.2px !important; padding:11px 26px !important; animation:none !important; }',
                '& .vtool-btn{ border-radius:8px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(163,230,53,0.16) !important;',
                '  border-color:var(--ff-a) !important; color:var(--ff-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
