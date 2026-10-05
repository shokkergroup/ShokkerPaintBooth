/* ============================================================================
 * EXPERIENCE 14 — HEADS-UP
 * Paradigm: GLASS OVERLAY. Cockpit HUD — chrome is translucent, the work is not.
 *
 * Distinct from Studio (which HIDES chrome until relevant): Heads-Up keeps
 * everything on screen permanently, but renders it as frosted glass with a
 * luminous edge so the artwork reads through the interface rather than beside
 * it. The rails still hold their own columns — the owner's rule is absolute, so
 * nothing floats on top of SOURCE or LIVE PREVIEW; the glass is applied to the
 * panels in place.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '14-headsup',
        name: 'Heads-Up',
        tagline: 'Frosted glass cockpit. Everything visible, nothing heavy.',
        paradigm: 'Translucent HUD',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // A HUD has edge instrumentation, not sidebars. Both rails become
            // narrow glass strips that widen on approach, so the canvas runs
            // nearly edge to edge and the silhouette is unmistakably its own.

            ctx.addClass(document.body, 'xp-hu-edges');

            // Corner brackets around each plate — the classic HUD reticle.
            ['#splitSource', '#splitPreview'].forEach(function (sel) {
                var box = ctx.q(sel);
                if (box) ctx.addClass(box, 'xp-hu-reticle');
            });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:12px; --hu-a:#31e0d4; --hu-warn:#ffb45c;',
                '   --hu-glass:rgba(14,26,34,0.55); }',
                '& #splitViewContainer{ padding:14px !important; gap:14px; }',

                /* a lit environment so glass has something to refract */
                '& .main-container{ background:',
                '  radial-gradient(1100px 600px at 22% 12%, #123037 0%, transparent 60%),',
                '  radial-gradient(900px 700px at 84% 88%, #10233a 0%, transparent 62%),',
                '  #060d12 !important; }',
                '& #centerPanel, & #canvasViewport{ background:transparent !important; }',

                /* frosted glass panels */
                '& .header, & #spbTopToolbar, & .left-panel, & .right-panel,',
                '& .xp-hu-strip, & .settings-dropdown, & .spb-tb-pop{',
                '  background:var(--hu-glass) !important;',
                '  backdrop-filter:blur(18px) saturate(1.3) !important;',
                '  -webkit-backdrop-filter:blur(18px) saturate(1.3) !important;',
                '  border-color:rgba(49,224,212,0.20) !important; }',
                '&.xp-hu-edges .left-panel, &.xp-hu-edges .right-panel{',
                '  transition:width .2s ease, min-width .2s ease, max-width .2s ease !important;',
                '  overflow:hidden !important; }',
                '&.xp-hu-edges .left-panel:hover, &.xp-hu-edges .left-panel:focus-within{',
                '  width:236px !important; min-width:236px !important; max-width:236px !important;',
                '  overflow-y:auto !important; z-index:140 !important; }',
                '&.xp-hu-edges .right-panel:hover, &.xp-hu-edges .right-panel:focus-within{',
                '  width:296px !important; min-width:296px !important; max-width:296px !important;',
                '  overflow-y:auto !important; z-index:140 !important; }',
                '& .left-panel{ border-right:1px solid rgba(49,224,212,0.22) !important;',
                '  box-shadow:1px 0 24px rgba(49,224,212,0.10) !important; }',
                '& .right-panel{ border-left:1px solid rgba(49,224,212,0.22) !important;',
                '  box-shadow:-1px 0 24px rgba(49,224,212,0.10) !important; }',
                '& .header{ border-bottom:1px solid rgba(49,224,212,0.22) !important; }',

                /* controls are outlines with a glow, never filled slabs */
                '& .btn, & .vtool-btn, & .zone-card, & .layer-row, & .rp-tab{',
                '  background:rgba(255,255,255,0.04) !important;',
                '  border:1px solid rgba(49,224,212,0.22) !important;',
                '  border-radius:10px !important; color:#d8f6f3 !important;',
                '  backdrop-filter:blur(6px); animation:none !important; }',
                '& .vtool-btn:hover, & .btn:hover{ border-color:var(--hu-a) !important;',
                '  box-shadow:0 0 14px rgba(49,224,212,0.28) !important; }',
                '& .vtool-btn.active{ background:rgba(49,224,212,0.16) !important;',
                '  border-color:var(--hu-a) !important; color:var(--hu-a) !important;',
                '  box-shadow:0 0 18px rgba(49,224,212,0.4), inset 0 0 18px rgba(49,224,212,0.12) !important;',
                '  animation:none !important; }',
                '& .zone-card.selected, & .zone-card.active{ border-color:var(--hu-warn) !important;',
                '  box-shadow:0 0 16px rgba(255,180,92,0.3) !important; }',

                /* the plates: dark, crisp, with HUD corner brackets */
                '& #splitSource, & #splitPreview{',
                '  background:rgba(2,8,12,0.72) !important;',
                '  border:1px solid rgba(49,224,212,0.32) !important; border-radius:12px !important;',
                '  box-shadow:0 0 0 1px rgba(0,0,0,0.5), 0 0 40px rgba(49,224,212,0.12) !important;',
                '  position:relative !important; overflow:visible !important; }',
                '& .xp-hu-reticle::before, & .xp-hu-reticle::after{',
                '  content:""; position:absolute; width:22px; height:22px; pointer-events:none;',
                '  border:2px solid var(--hu-a); opacity:0.85; }',
                '& .xp-hu-reticle::before{ left:-5px; top:-5px;',
                '  border-right:none; border-bottom:none; border-radius:4px 0 0 0; }',
                '& .xp-hu-reticle::after{ right:-5px; bottom:-5px;',
                '  border-left:none; border-top:none; border-radius:0 0 4px 0; }',
                '& .split-pane-label, & .preview-dual-label{',
                '  background:rgba(6,16,22,0.8) !important; color:var(--hu-a) !important;',
                '  border:1px solid rgba(49,224,212,0.3) !important; border-radius:6px !important;',
                '  letter-spacing:2px !important; backdrop-filter:blur(8px) !important; }',

                '& .xp-hu-strip{ flex:0 0 auto !important; gap:12px !important;',
                '  padding:8px 14px !important; min-height:0 !important;',
                '  border:1px solid rgba(49,224,212,0.22) !important; border-radius:12px !important; }',
                '& .xp-hu-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:10px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-hu-strip .spec-channel-dock-cell{ background:rgba(2,8,12,0.7) !important;',
                '  border:1px solid rgba(49,224,212,0.3) !important; border-radius:8px !important; }',
                '& .xp-hu-strip .spec-channel-dock-label{ background:rgba(6,16,22,0.85) !important;',
                '  color:var(--hu-a) !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:9px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:rgba(49,224,212,0.16) !important; color:var(--hu-a) !important;',
                '  border:1.5px solid var(--hu-a) !important; border-radius:10px !important;',
                '  font-weight:800 !important; letter-spacing:2px !important; padding:11px 28px !important;',
                '  box-shadow:0 0 24px rgba(49,224,212,0.35), inset 0 0 20px rgba(49,224,212,0.12) !important;',
                '  animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
