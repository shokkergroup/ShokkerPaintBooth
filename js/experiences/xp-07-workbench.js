/* ============================================================================
 * EXPERIENCE 07 — WORKBENCH
 * Paradigm: TACTILE. Tools are objects hanging on a pegboard, not icons in a bar.
 *
 * Every other experience treats tools as abstract commands. Workbench treats
 * them as things: the toolbar leaves the top of the screen entirely and becomes
 * a vertical PEGBOARD down the left of the canvas, with drilled holes, physical
 * button caps and a shadow that lifts when you pick one up. The surround is
 * warm steel and wood instead of black glass.
 *
 * The pegboard is a real relocation of the real #spbTopToolbar node, so every
 * tool keeps its handler — they just hang somewhere you can reach without
 * crossing the whole screen.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '07-workbench',
        name: 'Workbench',
        tagline: 'Tools hang on a pegboard beside the work, not in a bar above it.',
        paradigm: 'Tactile pegboard rail',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            /* PEGBOARD — the toolbar becomes a vertical rail beside the canvas.
             * It sits inside #centerPanel BEFORE #canvasViewport so it takes its
             * own column and never overlaps the artwork (owner rule). */
            var toolbar = ctx.q('#spbTopToolbar');
            var center = ctx.q('#centerPanel');
            if (toolbar && center) {
                var peg = ctx.mk('div', {
                    cls: 'xp-wb-peg spbx-scroll-y',
                    attrs: { 'aria-label': 'Tool pegboard' }
                });
                center.insertBefore(peg, center.firstChild);
                ctx.onTeardown(function () { if (peg.parentNode) peg.parentNode.removeChild(peg); });
                ctx.move(toolbar, peg);
                ctx.addClass(center, 'xp-wb-center');
            }

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:6px;',
                '   --wb-wood:#3a2a1c; --wb-steel:#4a4f56; --wb-brass:#c9a227; }',

                /* the bench surface */
                '& .main-container{ background:#241a12 !important; }',
                '& #centerPanel{',
                '  background:linear-gradient(180deg,#2e2118,#1d150e) !important; }',
                '& .header{ background:linear-gradient(180deg,#403022,#2b1f16) !important;',
                '  border-bottom:3px solid #17100a !important; }',
                '& .left-panel, & .right-panel{',
                '  background:linear-gradient(180deg,#332419,#241a12) !important;',
                '  border-color:#17100a !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,220,170,0.08) !important; }',

                /* the center becomes [pegboard][artwork] */
                '& #centerPanel.xp-wb-center{ flex-direction:row !important; align-items:stretch !important; }',
                '& #centerPanel.xp-wb-center > #canvasViewport{ flex:1 1 auto !important; min-width:0 !important; }',
                '& #centerPanel.xp-wb-center > .xp-wb-peg{ align-self:stretch !important; height:auto !important; }',
                '& .xp-wb-peg{',
                '  flex:0 0 92px; width:92px; padding:10px 6px;',
                /* drilled pegboard holes */
                '  background:',
                '    radial-gradient(circle at 12px 12px, #150e08 2.6px, transparent 3px) 0 0/24px 24px,',
                '    linear-gradient(180deg,#5a4430,#3d2c1d);',
                '  border-right:3px solid #17100a;',
                '  box-shadow:inset -6px 0 14px rgba(0,0,0,0.45);',
                /* the relocated toolbar overflowed this column by 63px and sat on
                   SOURCE — the owner rule is absolute, so clamp it hard. */
                '  overflow-x:auto !important; box-sizing:border-box; }',   /* scroll, never clip */
                '& .xp-wb-peg #spbTopToolbar{',
                '  display:flex !important; flex-direction:column !important;',
                '  align-items:stretch !important; gap:6px !important;',
                '  background:transparent !important; border:none !important;',
                '  padding:0 !important; height:auto !important;',
                '  width:100% !important; max-width:100% !important;',
                '  min-width:0 !important; overflow-x:visible !important;',
                '  box-sizing:border-box !important; }',
                '& .xp-wb-peg #spbTopToolbar > *{ max-width:100% !important; min-width:0 !important; }',
                '& .xp-wb-peg .vtool-group{ grid-template-columns:1fr 1fr !important;',
                '  border-bottom:1px solid rgba(0,0,0,0.4) !important; }',
                '& .xp-wb-peg .spb-tb-menu, & .xp-wb-peg details{ width:100% !important; }',

                /* tools are physical caps that lift when picked up */
                '& .vtool-btn{',
                '  border-radius:5px !important; animation:none !important;',
                '  background:linear-gradient(180deg,#6a7079,#3f444b) !important;',
                '  border:1px solid #14100c !important; color:#f0e6d8 !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.32), 0 3px 0 #23272c, 0 5px 8px rgba(0,0,0,0.5) !important;',
                '  transition:transform .07s ease, box-shadow .07s ease !important; }',
                '& .vtool-btn:hover{ transform:translateY(-1px);',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.4), 0 4px 0 #23272c, 0 7px 12px rgba(0,0,0,0.55) !important; }',
                '& .vtool-btn:active{ transform:translateY(3px);',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.2), 0 0 0 #23272c, 0 2px 4px rgba(0,0,0,0.5) !important; }',
                '& .vtool-btn.active{',
                '  background:linear-gradient(180deg,#e0bb45,#a37f12) !important; color:#1c1408 !important;',
                '  border-color:#6b5209 !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.5), 0 3px 0 #6b5209, 0 0 16px rgba(201,162,39,0.4) !important;',
                '  animation:none !important; }',

                /* the work itself sits in a steel frame */
                '& #splitViewContainer{ padding:10px !important; gap:10px; }',
                '& #splitSource, & #splitPreview{',
                '  background:#100b07 !important;',
                '  border:6px solid var(--wb-steel) !important; border-radius:5px !important;',
                '  box-shadow:inset 0 0 0 1px #14100c, 0 10px 26px rgba(0,0,0,0.6) !important; }',

                /* parts tray */
                '& .xp-wb-tray{ flex:0 0 auto !important; gap:12px !important;',
                '  padding:8px 12px !important; min-height:0 !important;',
                '  background:linear-gradient(180deg,#4a4f56,#33373d) !important;',
                '  border:1px solid #17100a !important; border-radius:5px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.2) !important; }',
                '& .xp-wb-tray #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:10px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-wb-tray .spec-channel-dock-cell{ background:#0d0a07 !important;',
                '  border:2px solid #23272c !important; border-radius:3px !important;',
                '  box-shadow:inset 0 2px 6px rgba(0,0,0,0.8) !important; }',
                '& .xp-wb-tray .spec-channel-dock-label{ background:#23272c !important;',
                '  color:#d8cbb8 !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:linear-gradient(180deg,#d9482f,#9c2f1b) !important; color:#fff !important;',
                '  border:1px solid #5c1a0e !important; border-radius:5px !important;',
                '  font-weight:800 !important; letter-spacing:1.6px !important; padding:12px 28px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.3), 0 4px 0 #5c1a0e !important;',
                '  animation:none !important; }',
                '& #previewBottomBar .btn-render:active{ transform:translateY(3px);',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.2), 0 1px 0 #5c1a0e !important; }',

                '& .zone-card{ background:linear-gradient(180deg,#40301f,#2d2116) !important;',
                '  border:1px solid #17100a !important; border-radius:4px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,220,170,0.1) !important; }',
                '& .zone-card.selected, & .zone-card.active{',
                '  box-shadow:inset 0 1px 0 rgba(255,220,170,0.16), inset 4px 0 0 var(--wb-brass) !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
