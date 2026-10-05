/* ============================================================================
 * EXPERIENCE 01 — STUDIO
 * Paradigm: PROGRESSIVE DISCLOSURE. Chrome is present only when it is relevant.
 *
 * THE MEASURED PROBLEM (probed from the live app, 2026-07-29):
 *   The app sizes both sacred boxes as s = min((rowWidth - 8) / 2, rowHeight).
 *   In BOTH viewports the binding term is WIDTH, and the width is being eaten
 *   by chrome, not by the artwork:
 *     desktop 1920x1080  row 1102x673 -> 547x547   (126px of height sits unused)
 *     min     1100x800   row  306x393 -> 149x149   (244px of height sits unused)
 *   The dominant thief is one rule (paint-booth-v2.html:826): an open zone
 *   popout reserves a 320px column out of .center-panel. At 1100x800 that is
 *   49% of the center panel — the popout is given twice the width of the car.
 *
 * WHAT STUDIO DOES ABOUT IT:
 *   1. The zone popout keeps every control but becomes a right-rail INSPECTOR
 *      instead of carving a column out of the artwork. (Floating it over the
 *      canvas was tried first and rejected by measurement: it won the width
 *      back but then covered 100% of SOURCE at 1100x800, and its open state
 *      could not be held — collapseZoneDetail() clears both 'active' and
 *      'collapsed', and the next zone render re-opens it. Docking wins the
 *      width AND occludes nothing.)
 *   2. The 4 channel previews move BELOW the two boxes. Because the squares are
 *      width-limited with 126-244px of spare height, a compact strip there is
 *      geometrically FREE — it costs the sacred boxes nothing.
 *   3. Tool options and the render dock float over the canvas rather than
 *      stacking above it, and fade back when idle.
 *
 * Nothing is removed. Every tool, every control, all four channels — same DOM
 * nodes, same listeners, just given back the room they were taking from the car.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '01-studio',
        name: 'Studio',
        tagline: 'The quiet pro. Chrome disappears until you need it.',
        paradigm: 'Progressive disclosure',

        apply: function (ctx) {
            // One canonical skeleton (see Ctx.bench): ZONES + ZONE POPOUT left,
            // LAYERS right, channels under the artwork, everything permanently
            // visible. Studio adds only its look and feel on top.
            ctx.bench();

            ctx.css([
                '&{ --xp-ch:54px; --xp-radius:14px; --xp-accent:#e0913a; }',

                /* Reclaim the container padding too — at 1100 it is 24px of the
                   330px the artwork gets, i.e. 12px off each square's edge. */
                '& #splitViewContainer{ padding:6px !important; gap:6px; }',

                /* Header + toolbar recede to thin, quiet strips. */
                '& .header{ background:#0e1116 !important; border-bottom:1px solid var(--xp-line) !important; }',
                '& #spbTopToolbar{ background:#0b0e13 !important; border-bottom:1px solid var(--xp-line) !important; }',
                '& .vtool-btn{ border-radius:9px !important; animation:none !important; }',
                '& .vtool-btn.active{',
                '  background:rgba(224,145,58,0.16) !important;',
                '  border-color:var(--xp-accent) !important;',
                '  color:var(--xp-accent) !important;',
                '  box-shadow:none !important; animation:none !important;',
                '}',

                /* The two boxes framed like prints on a gallery wall. */
                '& #splitSource, & #splitPreview{',
                '  background:#0b0d12 !important;',
                '  border:1px solid rgba(255,255,255,0.08) !important;',
                '  box-shadow:0 18px 50px rgba(0,0,0,0.55) !important;',
                '}',
                '& #splitPreview{ border-left:1px solid rgba(255,255,255,0.08) !important; }',

                /* Channel strip below the artwork: compact, centred, square. */
                '& .xp-studio-strip{',
                '  flex:0 0 auto !important; justify-content:center !important;',
                '  padding:4px 8px !important; min-height:0 !important;',
                '  background:transparent !important; border:none !important;',
                '}',
                '& .xp-studio-strip #specChannelDock{',
                '  background:transparent !important; border:none !important;',
                '  padding:0 !important; justify-content:center !important;',
                '}',
                '& .xp-studio-strip .spec-channel-dock-cell{',
                '  border-color:rgba(255,255,255,0.10) !important; background:#0b0d12 !important;',
                '}',
                '& .xp-studio-strip .spec-channel-dock-cell:hover{ border-color:var(--xp-accent) !important; }',

                /* Floating action dock — quieter frame, louder RENDER. */
                '& .xp-studio-dock{',
                '  padding:6px 10px !important; gap:8px !important; height:auto !important;',
                '  min-height:0 !important; max-height:none !important; flex:0 0 auto !important;',
                '}',
                '& .xp-studio-dock .btn-render{',
                '  background:linear-gradient(180deg,#f0a24a,#d07c22) !important;',
                '  color:#150d03 !important; border:none !important;',
                '  font-weight:800 !important; letter-spacing:0.6px !important;',
                '  border-radius:10px !important; padding:8px 22px !important;',
                '  box-shadow:0 6px 20px rgba(224,145,58,0.35) !important;',
                '  animation:none !important;',
                '}',
                '& .xp-studio-hud{ padding:3px 10px !important; height:auto !important; }',

                /* Rails: quiet cards instead of hard-bordered boxes. */
                '& .left-panel, & .right-panel{ background:#0c0f14 !important; border-color:var(--xp-line) !important; }',
                /* the inspector column is the inner one; give it the divider */
                '&.xp-studio-onesided .right-panel{',
                '  border-left:1px solid var(--xp-line) !important;',
                '  border-right:2px solid rgba(224,145,58,0.25) !important; }',
                '&.xp-studio-onesided .left-panel{ border-right:1px solid var(--xp-line) !important; }',

                /* Studio is calm by definition — no ambient pulsing. */
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
