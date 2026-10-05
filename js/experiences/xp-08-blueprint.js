/* ============================================================================
 * EXPERIENCE 08 — BLUEPRINT
 * Paradigm: TECHNICAL DRAWING. The app is a drafting sheet, not a dark IDE.
 *
 * Everything becomes line art on drafting paper: nothing is filled, every panel
 * is an outlined plate with a title block, and the two sacred boxes get real
 * DIMENSION CALLOUTS reading 2048 x 2048 — the actual iRacing canvas size, which
 * is the single most useful fact about them and is currently written nowhere.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '08-blueprint',
        name: 'Blueprint',
        tagline: 'Drafting sheet. Dimensioned, annotated, all line art.',
        paradigm: 'Technical drawing',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // On a drawing sheet the detail views run down the right margin,
            // keyed to the main elevation — not along the bottom like a footer.
            // Same width arithmetic as Twin: safe against the size floor.

            // The right-margin detail column is gone: turning the artwork
            // container into a row fought the bench and cut the boxes to 120sq.
            // Blueprint keeps its dimension callouts and drafting grid.

            // Dimension callouts on the two boxes: 2048 x 2048 is the truth of
            // the file being produced, and a draughtsman would always mark it.
            ['#splitSource', '#splitPreview'].forEach(function (sel) {
                var box = ctx.q(sel);
                if (!box) return;
                ctx.addClass(box, 'xp-bp-dim');
                box.setAttribute('data-xp-dim', '2048 × 2048 px');
                ctx.onTeardown(function () { box.removeAttribute('data-xp-dim'); });
            });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:0px; --bp-ink:#8fd4ff; --bp-paper:#0a2138;',
                '   --bp-line:rgba(143,212,255,0.28); --bp-hot:#ffd166; }',

                /* drafting paper with a real grid */
                '& .main-container, & #centerPanel, & #canvasViewport{',
                '  background-color:var(--bp-paper) !important;',
                '  background-image:',
                '    linear-gradient(rgba(143,212,255,0.07) 1px, transparent 1px),',
                '    linear-gradient(90deg, rgba(143,212,255,0.07) 1px, transparent 1px),',
                '    linear-gradient(rgba(143,212,255,0.14) 1px, transparent 1px),',
                '    linear-gradient(90deg, rgba(143,212,255,0.14) 1px, transparent 1px) !important;',
                '  background-size:10px 10px, 10px 10px, 50px 50px, 50px 50px !important;',
                '}',
                '& .header, & #spbTopToolbar{ background:#08192b !important;',
                '  border-bottom:1px solid var(--bp-line) !important; }',
                '& .left-panel, & .right-panel{ background:rgba(8,25,43,0.82) !important;',
                '  border-color:var(--bp-line) !important; }',

                /* nothing is filled — everything is drawn */
                '& .btn, & .vtool-btn, & .zone-card, & .layer-row, & .rp-tab{',
                '  background:transparent !important; border-radius:0 !important;',
                '  border:1px solid var(--bp-line) !important; color:var(--bp-ink) !important;',
                '  animation:none !important; box-shadow:none !important; }',
                '& .vtool-btn.active, & .zone-card.selected, & .zone-card.active{',
                '  border-color:var(--bp-hot) !important; color:var(--bp-hot) !important;',
                '  background:rgba(255,209,102,0.08) !important; }',
                '& .panel-header, & .vtool-label, & .section-header-label, & .rp-tab{',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:1.6px !important; text-transform:uppercase !important;',
                '  color:var(--bp-ink) !important; }',

                /* the two plates, dimensioned */
                '& #splitViewContainer{ padding:26px 22px 14px !important; gap:26px; }',
                '& #splitSource, & #splitPreview{',
                '  background:rgba(4,14,26,0.6) !important;',
                '  border:1px solid var(--bp-ink) !important; border-radius:0 !important;',
                '  box-shadow:0 0 0 4px rgba(143,212,255,0.06) !important;',
                '  position:relative !important; overflow:visible !important; }',
                /* extension lines + the dimension text above each plate */
                '& .xp-bp-dim::before{',
                '  content:""; position:absolute; left:0; right:0; top:-13px; height:1px;',
                '  background:var(--bp-ink); opacity:0.6;',
                '  box-shadow:0 -4px 0 -3px var(--bp-ink), 0 4px 0 -3px var(--bp-ink); }',
                '& .xp-bp-dim::after{',
                '  content:attr(data-xp-dim); position:absolute; left:50%; top:-27px;',
                '  transform:translateX(-50%); padding:0 8px; background:var(--bp-paper);',
                '  font:600 9px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  letter-spacing:1.4px; color:var(--bp-ink); white-space:nowrap; }',
                '& .split-pane-label, & .preview-dual-label{',
                '  background:var(--bp-paper) !important; color:var(--bp-hot) !important;',
                '  border:1px solid var(--bp-line) !important; border-radius:0 !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:2px !important; }',

                /* title-block strip */
                /* the sheet lays out as [drawing | detail margin] */
                '& #splitViewContainer.xp-bp-sheet{ flex-direction:row !important;',
                '  align-items:stretch !important; }',
                '& .xp-bp-details{ flex:0 0 78px !important; width:78px !important;',
                '  display:flex !important; flex-direction:column !important;',
                '  align-items:center !important; justify-content:flex-start !important;',
                '  gap:10px !important; padding:10px 4px !important; min-height:0 !important;',
                '  border-left:1px solid var(--bp-line) !important; }',
                '& .xp-bp-details #specChannelDock{ flex-direction:column !important; }',
                '& .xp-bp-details .spec-channel-dock-cells{ flex-direction:column !important;',
                '  align-items:center !important; gap:10px !important; }',
                '& .xp-bp-plate{ flex:0 0 auto !important; gap:12px !important;',
                '  padding:7px 12px !important; min-height:0 !important;',
                '  background:rgba(8,25,43,0.9) !important;',
                '  border:1px solid var(--bp-ink) !important; border-radius:0 !important; }',
                '& .xp-bp-plate #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:10px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-bp-plate .spec-channel-dock-cell{ background:rgba(4,14,26,0.7) !important;',
                '  border:1px solid var(--bp-ink) !important; border-radius:0 !important; }',
                '& .xp-bp-plate .spec-channel-dock-label{ background:var(--bp-paper) !important;',
                '  color:var(--bp-ink) !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:transparent !important; color:var(--bp-hot) !important;',
                '  border:2px solid var(--bp-hot) !important; border-radius:0 !important;',
                '  font:700 12px/1 ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:3px !important; padding:11px 26px !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& #previewBottomBar .btn-render:hover{ background:rgba(255,209,102,0.12) !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
