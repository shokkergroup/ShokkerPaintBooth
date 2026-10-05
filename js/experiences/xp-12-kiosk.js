/* ============================================================================
 * EXPERIENCE 12 — KIOSK
 * Paradigm: BIG TOUCH. Built for the person who finds the app intimidating.
 *
 * Not "simple mode" — nothing is removed. Everything gets BIGGER: 44px minimum
 * hit targets (the accessibility floor), 15px body text, high contrast, and
 * generous spacing. The density that makes the pro layout efficient is exactly
 * what makes it unapproachable, so Kiosk trades density for confidence and lets
 * the rails scroll instead of shrink.
 *
 * This is the most direct answer to "make it more accessible for people but do
 * NOT strip away features".
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '12-kiosk',
        name: 'Kiosk',
        tagline: 'Everything bigger. 44px targets, high contrast, nothing removed.',
        paradigm: 'Big-touch accessibility',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // One place for everything. Two rails means deciding which side a
            // control is on before you can look for it — the opposite of what
            // this experience is for. Zones stack above finishes in a single
            // wide right column, and the left rail disappears entirely.
            // tabs:false — this pack deliberately stacks zones + finishes +
            // inspector in ONE column; tabbing them would re-hide what it
            // exists to put in one place.

            var leftRail = ctx.q('#leftPanel');
            var rightRail = ctx.q('#rightPanel');
            if (leftRail && rightRail) {
                ctx.move(leftRail, rightRail, { before: rightRail.firstElementChild });
                ctx.addClass(leftRail, 'xp-ki-merged');
            }

            // Rails must SCROLL, not clip — bigger controls in the same width
            // means more overflow, and a clipped tool is a removed tool.
            ['#leftPanel', '#rightPanel', '#spbTopToolbar'].forEach(function (sel) {
                ctx.addClass(sel, 'spbx-scroll-y');
            });

            ctx.css([
                '&{ --xp-ch:58px; --xp-radius:14px; --ki-a:#2f9bff; --ki-ink:#f2f6fb; }',
                '& #splitViewContainer{ padding:10px !important; gap:10px; }',
                '& .main-container, & #centerPanel{ background:#0f151c !important; }',
                '& .header, & #spbTopToolbar{ background:#141c26 !important;',
                '  border-bottom:2px solid #24313f !important; }',
                '& .right-panel{ background:#141c26 !important; border-color:#24313f !important; }',
                '& #leftPanel.xp-ki-merged{',
                '  width:100% !important; min-width:0 !important; max-width:none !important;',
                '  flex:0 0 auto !important; max-height:46% !important;',
                '  border-right:none !important; border-bottom:2px solid #24313f !important;',
                '  background:transparent !important; overflow-y:auto !important; }',

                /* THE ACCESSIBILITY FLOOR — 44px targets everywhere */
                '& .vtool-btn{ min-height:44px !important; min-width:44px !important;',
                '  font-size:19px !important; border-radius:12px !important;',
                '  border:2px solid #2c3b4d !important; background:#1b2531 !important;',
                '  color:var(--ki-ink) !important; animation:none !important; }',
                '& .vtool-btn.active{ background:var(--ki-a) !important; color:#06111d !important;',
                '  border-color:#7fc4ff !important; box-shadow:0 0 0 3px rgba(47,155,255,0.28) !important;',
                '  animation:none !important; }',
                '& .btn, & button{ min-height:40px !important; font-size:14px !important;',
                '  border-radius:11px !important; }',
                '& .btn-sm{ min-height:36px !important; font-size:13px !important; }',
                '& input[type="text"], & input[type="number"], & select, & textarea{',
                '  min-height:42px !important; font-size:15px !important; border-radius:10px !important; }',
                '& input[type="checkbox"], & input[type="radio"]{',
                '  width:24px !important; height:24px !important; }',
                '& input[type="range"]{ height:34px !important; }',
                '& input[type="range"]::-webkit-slider-runnable-track{ height:10px; border-radius:6px;',
                '  background:#24313f; }',
                '& input[type="range"]::-webkit-slider-thumb{ -webkit-appearance:none;',
                '  width:28px; height:28px; margin-top:-9px; border-radius:50%;',
                '  background:var(--ki-a); border:3px solid #0f151c;',
                '  box-shadow:0 2px 8px rgba(0,0,0,0.5); }',

                /* readable type, generous rhythm */
                '& .panel-header{ font-size:14px !important; letter-spacing:1px !important;',
                '  padding:12px 14px !important; color:var(--ki-ink) !important; }',
                '& .zone-card{ min-height:60px !important; padding:12px !important;',
                '  border-radius:14px !important; font-size:15px !important;',
                '  background:#1b2531 !important; border:2px solid #2c3b4d !important;',
                '  margin-bottom:8px !important; }',
                '& .zone-card.selected, & .zone-card.active{ border-color:var(--ki-a) !important;',
                '  box-shadow:0 0 0 3px rgba(47,155,255,0.25) !important; }',
                '& .layer-row{ min-height:52px !important; font-size:14px !important;',
                '  border-radius:11px !important; }',
                '& .rp-tab{ min-height:44px !important; font-size:13px !important; }',
                '& .section-header{ min-height:48px !important; font-size:14px !important; }',
                '& .section-header-label{ font-size:14px !important; letter-spacing:0.6px !important; }',

                /* high contrast focus ring — keyboard users get a real one */
                '& *:focus-visible{ outline:3px solid #ffd54a !important; outline-offset:2px !important; }',

                '& #splitSource, & #splitPreview{ background:#080d13 !important;',
                '  border:3px solid #24313f !important; border-radius:16px !important; }',
                '& .split-pane-label, & .preview-dual-label{ font-size:13px !important;',
                '  padding:6px 12px !important; letter-spacing:1.2px !important; }',

                '& .xp-ki-strip{ flex:0 0 auto !important; gap:14px !important;',
                '  padding:10px 14px !important; min-height:0 !important;',
                '  background:#141c26 !important; border:2px solid #24313f !important;',
                '  border-radius:14px !important; }',
                '& .xp-ki-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:14px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-ki-strip .spec-channel-dock-cell{ background:#080d13 !important;',
                '  border:2px solid #2c3b4d !important; border-radius:10px !important; }',
                '& .xp-ki-strip .spec-channel-dock-label{ font-size:8px !important;',
                '  background:#1b2531 !important; color:#a9bed3 !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:10px !important;',
                '  flex-wrap:wrap !important; }',
                '& #previewBottomBar .btn-render{ min-height:56px !important;',
                '  background:var(--ki-a) !important; color:#06111d !important; border:none !important;',
                '  border-radius:14px !important; font-size:17px !important; font-weight:800 !important;',
                '  letter-spacing:1.4px !important; padding:0 40px !important; animation:none !important;',
                '  box-shadow:0 6px 20px rgba(47,155,255,0.35) !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
