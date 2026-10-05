/* ============================================================================
 * EXPERIENCE 18 — ZEN
 * Paradigm: SINGLE-PANEL FOCUS. Exactly one rail is awake at a time.
 *
 * Distinct from Studio (chrome fades until relevant) and Heads-Up (everything
 * visible but translucent): Zen keeps both rails MOUNTED and full width, but
 * only the one you are pointing at is legible — the other dims to a spine. The
 * artwork is never dimmed. It is the quietest possible way to work without
 * hiding a single control, and it is the only experience that makes the two
 * boxes brighter than everything else on the screen by construction.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '18-zen',
        name: 'Zen',
        tagline: 'One rail awake at a time. The car is the only bright thing.',
        paradigm: 'Single-panel focus',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // Zen and Command both reduce chrome, so they must not reduce it the
            // same way. Command keeps 26px labelled spines that expand on hover.
            // Zen goes further: 20px unlabelled edges, no expansion until you
            // actually point at them, and the artwork sits in near-black.

            ctx.addClass(document.body, 'xp-zn-spines');

            // Whichever rail the pointer is over becomes the awake one; it stays
            // awake while focus is inside it, so keyboard users are not punished.
            var RAILS = ['#leftPanel', '#rightPanel', '#spbTopToolbar'];
            var awake = null, t = null;
            function setAwake(el) {
                if (awake === el) return;
                RAILS.forEach(function (s) {
                    document.querySelectorAll(s).forEach(function (n) { n.classList.remove('xp-zn-awake'); });
                });
                if (el) el.classList.add('xp-zn-awake');
                awake = el;
            }
            RAILS.forEach(function (sel) {
                var el = ctx.q(sel);
                if (!el) return;
                ctx.on(el, 'pointerenter', function () { clearTimeout(t); setAwake(el); });
                ctx.on(el, 'focusin', function () { clearTimeout(t); setAwake(el); });
                ctx.on(el, 'pointerleave', function () {
                    clearTimeout(t);
                    t = setTimeout(function () {
                        if (!el.contains(document.activeElement)) setAwake(null);
                    }, 420);
                });
            });
            ctx.addClass(document.body, 'xp-zn-on');
            ctx.onTeardown(function () {
                clearTimeout(t);
                document.querySelectorAll('.xp-zn-awake').forEach(function (n) {
                    n.classList.remove('xp-zn-awake');
                });
            });

            ctx.css([
                '&{ --xp-ch:48px; --xp-radius:6px; --zn-a:#e6e6e6; --zn-dim:#3a3a3a; }',
                '& #splitViewContainer{ padding:18px !important; gap:18px; }',
                '& .main-container, & #centerPanel, & #canvasViewport{ background:#000 !important; }',
                '& .header, & #spbTopToolbar{ background:#050505 !important;',
                '  border-bottom:1px solid #161616 !important; }',
                '& .left-panel, & .right-panel{ background:#050505 !important; border-color:#161616 !important; }',

                /* asleep: readable enough to find, quiet enough to ignore */
                '&.xp-zn-on .left-panel, &.xp-zn-on .right-panel, &.xp-zn-on #spbTopToolbar{',
                '  opacity:0.30; filter:saturate(0.25);',
                '  transition:opacity .28s ease, filter .28s ease; }',
                '&.xp-zn-spines .left-panel, &.xp-zn-spines .right-panel{',
                '  overflow:hidden !important;',
                '  transition:width .26s ease, min-width .26s ease, max-width .26s ease,',
                '             opacity .26s ease !important; }',
                '&.xp-zn-spines .left-panel:hover, &.xp-zn-spines .left-panel:focus-within{',
                '  width:222px !important; min-width:222px !important; max-width:222px !important;',
                '  overflow-y:auto !important; z-index:140 !important; }',
                '&.xp-zn-spines .right-panel:hover, &.xp-zn-spines .right-panel:focus-within{',
                '  width:282px !important; min-width:282px !important; max-width:282px !important;',
                '  overflow-y:auto !important; z-index:140 !important; }',
                '&.xp-zn-on .xp-zn-awake{ opacity:1 !important; filter:none !important; }',
                /* the header is always legible — it holds the file paths */
                '&.xp-zn-on .header{ opacity:0.72; }',
                '&.xp-zn-on .header:hover{ opacity:1; }',

                /* monochrome, hairline, nothing shouts */
                '& .btn, & .vtool-btn, & .zone-card, & .layer-row, & .rp-tab{',
                '  background:transparent !important; color:#c8c8c8 !important;',
                '  border:1px solid #202020 !important; border-radius:6px !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .vtool-btn.active{ background:#141414 !important; color:#fff !important;',
                '  border-color:#4a4a4a !important; animation:none !important; }',
                '& .zone-card.selected, & .zone-card.active{ border-color:#5a5a5a !important;',
                '  box-shadow:inset 2px 0 0 #d0d0d0 !important; }',
                '& .panel-header, & .rp-tab, & .section-header-label{',
                '  color:#7a7a7a !important; letter-spacing:1.6px !important;',
                '  font-weight:500 !important; }',

                /* the artwork is never dimmed — it is the point */
                '& #splitSource, & #splitPreview{ background:#000 !important;',
                '  border:1px solid #232323 !important; border-radius:6px !important;',
                '  box-shadow:0 0 0 1px #000, 0 26px 70px rgba(0,0,0,0.9) !important;',
                '  opacity:1 !important; filter:none !important; }',
                '& .split-pane-label, & .preview-dual-label{ background:transparent !important;',
                '  color:#6a6a6a !important; border:none !important; letter-spacing:3px !important;',
                '  font-weight:400 !important; }',

                '& .xp-zn-strip{ flex:0 0 auto !important; justify-content:center !important;',
                '  gap:16px !important; padding:8px 12px !important; min-height:0 !important;',
                '  background:transparent !important; border:none !important; }',
                '& .xp-zn-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:14px !important; }',
                '& .xp-zn-strip .spec-channel-dock-cell{ background:#000 !important;',
                '  border:1px solid #232323 !important; border-radius:4px !important; }',
                '& .xp-zn-strip .spec-channel-dock-label{ background:#0a0a0a !important;',
                '  color:#5a5a5a !important; border-bottom:1px solid #1a1a1a !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important;',
                '  display:flex !important; align-items:center !important; gap:10px !important; }',
                '& #previewBottomBar .btn-render{ background:transparent !important; color:#e6e6e6 !important;',
                '  border:1px solid #4a4a4a !important; border-radius:6px !important;',
                '  font-weight:500 !important; letter-spacing:4px !important; padding:11px 30px !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& #previewBottomBar .btn-render:hover{ background:#141414 !important; border-color:#8a8a8a !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
