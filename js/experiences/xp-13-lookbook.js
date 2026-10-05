/* ============================================================================
 * EXPERIENCE 13 — LOOKBOOK
 * Paradigm: EDITORIAL BROWSE. A design magazine, not a control panel.
 *
 * The only LIGHT experience in the set, deliberately: every other paint tool on
 * the market is dark, and a light editorial surface makes colour read honestly —
 * you judge a candy red against paper, not against black glass. Serif display
 * type, wide margins, hairline rules, and the finish lists laid out like a
 * lookbook spread rather than a dense grid of chips.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '13-lookbook',
        name: 'Lookbook',
        tagline: 'Light editorial spread. Judge colour against paper, not black.',
        paradigm: 'Editorial browse (light)',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            // A masthead gives the spread its editorial anchor.
            var head = ctx.mk('div', {
                cls: 'xp-lb-masthead', into: '#centerPanel', first: true,
                html: '<span class="xp-lb-title">The Paint Booth</span>' +
                      '<span class="xp-lb-rule"></span>' +
                      '<span class="xp-lb-sub">Source &amp; Live Preview — 2048 × 2048</span>'
            });
            void head;

            ctx.css([
                '&{ --xp-ch:54px; --xp-radius:2px;',
                '   --lb-paper:#f6f3ec; --lb-ink:#1b1a17; --lb-mid:#6c675e;',
                '   --lb-rule:#d8d2c6; --lb-accent:#a8321f;',
                '   --xp-ink:#1b1a17; --xp-dim:#6c675e; --xp-line:#d8d2c6; }',

                /* paper */
                '& .main-container, & #centerPanel, & #canvasViewport{ background:var(--lb-paper) !important; }',
                '& .header, & #spbTopToolbar{ background:#fffdf8 !important;',
                '  border-bottom:1px solid var(--lb-rule) !important; color:var(--lb-ink) !important; }',
                '& .left-panel, & .right-panel{ background:#fffdf8 !important;',
                '  border-color:var(--lb-rule) !important; }',

                /* editorial type */
                '& .header *, & .panel-header, & .rp-tab, & .zone-card, & .layer-row,',
                '& .section-header-label, & .btn, & label, & .vtool-label{',
                '  color:var(--lb-ink) !important; }',
                '& .panel-header, & .section-header-label{',
                '  font-family:Georgia,"Iowan Old Style",serif !important;',
                '  font-size:13px !important; letter-spacing:0.6px !important;',
                '  text-transform:none !important; font-weight:600 !important; }',
                '& .xp-lb-masthead{ flex:0 0 auto; display:flex; align-items:baseline; gap:14px;',
                '  padding:14px 22px 10px; background:var(--lb-paper);',
                '  border-bottom:1px solid var(--lb-rule); }',
                '& .xp-lb-title{ font:600 25px/1 Georgia,"Iowan Old Style",serif;',
                '  color:var(--lb-ink); letter-spacing:-0.4px; }',
                '& .xp-lb-rule{ flex:1 1 auto; height:1px; background:var(--lb-rule); }',
                '& .xp-lb-sub{ font:400 10.5px/1 Georgia,serif; color:var(--lb-mid);',
                '  letter-spacing:1.6px; text-transform:uppercase; }',

                /* hairline everything; no boxes-in-boxes */
                '& .zone-card, & .layer-row, & .btn, & .vtool-btn, & .rp-tab{',
                '  background:transparent !important; border-radius:2px !important;',
                '  box-shadow:none !important; animation:none !important;',
                '  border:1px solid var(--lb-rule) !important; }',
                '& .zone-card{ padding:10px 12px !important; margin-bottom:7px !important;',
                '  font-family:Georgia,serif !important; }',
                '& .zone-card.selected, & .zone-card.active{',
                '  border-color:var(--lb-accent) !important;',
                '  box-shadow:inset 3px 0 0 var(--lb-accent) !important;',
                '  background:#fff !important; }',
                '& .vtool-btn{ color:#3b382f !important; }',
                '& .vtool-btn:hover{ background:#efe9dd !important; }',
                '& .vtool-btn.active{ background:var(--lb-accent) !important; color:#fff !important;',
                '  border-color:var(--lb-accent) !important; animation:none !important; }',
                '& input[type="text"], & input[type="number"], & select, & textarea{',
                '  background:#fff !important; color:var(--lb-ink) !important;',
                '  border:1px solid var(--lb-rule) !important; border-radius:2px !important; }',

                /* the plates: white mount, thin rule, generous margin */
                '& #splitViewContainer{ padding:22px 26px 14px !important; gap:26px; }',
                '& #splitSource, & #splitPreview{',
                '  background:#fff !important;',
                '  border:1px solid var(--lb-rule) !important; border-radius:2px !important;',
                '  box-shadow:0 1px 2px rgba(27,26,23,0.06), 0 12px 30px rgba(27,26,23,0.10) !important; }',
                '& .split-pane-label, & .preview-dual-label{',
                '  background:#fff !important; color:var(--lb-mid) !important;',
                '  border:none !important; border-bottom:1px solid var(--lb-rule) !important;',
                '  font:400 9px/1.8 Georgia,serif !important; letter-spacing:2.4px !important;',
                '  text-transform:uppercase !important; }',

                '& .xp-lb-plate{ flex:0 0 auto !important; justify-content:center !important;',
                '  gap:20px !important; padding:10px 16px !important; min-height:0 !important;',
                '  background:transparent !important; border:none !important;',
                '  border-top:1px solid var(--lb-rule) !important; }',
                '& .xp-lb-plate #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:18px !important; }',
                '& .xp-lb-plate .spec-channel-dock-cell{ background:#fff !important;',
                '  border:1px solid var(--lb-rule) !important; border-radius:2px !important;',
                '  box-shadow:0 2px 8px rgba(27,26,23,0.08) !important; }',
                '& .xp-lb-plate .spec-channel-dock-label{ background:#fff !important;',
                '  color:var(--lb-mid) !important; font-family:Georgia,serif !important;',
                '  border-bottom:1px solid var(--lb-rule) !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important;',
                '  display:flex !important; align-items:center !important; gap:10px !important; }',
                '& #previewBottomBar .btn-render{ background:var(--lb-accent) !important;',
                '  color:#fff !important; border:none !important; border-radius:2px !important;',
                '  font:600 12px/1 Georgia,serif !important; letter-spacing:2.6px !important;',
                '  padding:12px 30px !important; animation:none !important; box-shadow:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }',
                /* the app assumes a dark canvas in a few spots — keep text legible */
                '& .settings-dropdown, & .spb-tb-pop{ background:#fffdf8 !important;',
                '  border-color:var(--lb-rule) !important; color:var(--lb-ink) !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
