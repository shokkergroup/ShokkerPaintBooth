/* ============================================================================
 * EXPERIENCE 16 — TWIN
 * Paradigm: COMPARATIVE. The two boxes are formally A and B, with tools for
 * reading the difference between them.
 *
 * Darkroom magnifies detail; Twin compares. It labels SOURCE as A and LIVE
 * PREVIEW as B, links their scroll so you are always looking at the same part
 * of the car in both, and adds a SWAP-FLICKER: hold the key and B is drawn over
 * A at the same size, so a change reads as motion rather than as two pictures
 * you have to hold in your head. That is how retouchers actually A/B.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '16-twin',
        name: 'Twin',
        tagline: 'A/B the two boxes: linked scroll, hold F to flicker between them.',
        paradigm: 'Comparative A/B',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // The four channels belong BETWEEN the two things being compared —
            // a shared reference column, not a footer. Costs ~70px of width;
            // checked against the floor first: (1426-78)/2 = 674 desktop and
            // (630-78)/2 = 276 at 1100x800, both above 547/149.

            // The channel reference column is gone for the same reason as
            // Blueprint's. Twin's identity is the A/B pairing itself: labels,
            // linked scroll and hold-F flicker.

            var A = ctx.q('#splitSource'), B = ctx.q('#splitPreview');
            if (A) { ctx.addClass(A, 'xp-tw-a'); A.setAttribute('data-xp-ab', 'A · SOURCE'); }
            if (B) { ctx.addClass(B, 'xp-tw-b'); B.setAttribute('data-xp-ab', 'B · LIVE'); }
            ctx.onTeardown(function () {
                [A, B].forEach(function (n) { if (n) n.removeAttribute('data-xp-ab'); });
            });

            /* LINKED SCROLL — comparing is meaningless if the two panes are
             * looking at different parts of the car. */
            var syncing = false;
            function link(from, to) {
                if (!from || !to) return;
                ctx.on(from, 'scroll', function () {
                    if (syncing) return;
                    syncing = true;
                    var fx = from.scrollWidth - from.clientWidth;
                    var fy = from.scrollHeight - from.clientHeight;
                    var tx = to.scrollWidth - to.clientWidth;
                    var ty = to.scrollHeight - to.clientHeight;
                    if (fx > 0 && tx > 0) to.scrollLeft = (from.scrollLeft / fx) * tx;
                    if (fy > 0 && ty > 0) to.scrollTop = (from.scrollTop / fy) * ty;
                    requestAnimationFrame(function () { syncing = false; });
                });
            }
            link(A, B); link(B, A);

            /* FLICKER — hold F and B is overlaid on A at identical size, so a
             * difference reads as movement. Release to drop back. */
            var flicking = false;
            ctx.on(document, 'keydown', function (e) {
                if (e.key !== 'f' && e.key !== 'F') return;
                if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
                if (flicking) return;
                flicking = true;
                document.body.classList.add('xp-tw-flick');
            });
            ctx.on(document, 'keyup', function (e) {
                if (e.key !== 'f' && e.key !== 'F') return;
                flicking = false;
                document.body.classList.remove('xp-tw-flick');
            });
            ctx.onTeardown(function () { document.body.classList.remove('xp-tw-flick'); });

            var hint = ctx.mk('div', {
                cls: 'xp-tw-hint', into: '#centerPanel',
                html: '<b>A</b> source &nbsp;·&nbsp; <b>B</b> live &nbsp;·&nbsp; ' +
                      'scroll is linked &nbsp;·&nbsp; hold <kbd>F</kbd> to flicker B over A'
            });
            void hint;

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:8px; --tw-a:#38bdf8; --tw-b:#fb7185; }',
                '& #splitViewContainer{ padding:10px !important; gap:10px; }',
                '& .main-container, & #centerPanel{ background:#0a0f14 !important; }',
                '& .header, & #spbTopToolbar{ background:#0e151c !important;',
                '  border-bottom:1px solid #1e2a36 !important; }',
                '& .left-panel, & .right-panel{ background:#0e151c !important; border-color:#1e2a36 !important; }',

                /* A and B get their own identity colour */
                '& #splitSource, & #splitPreview{ background:#05080b !important;',
                '  border-radius:8px !important; position:relative !important;',
                '  box-shadow:0 12px 34px rgba(0,0,0,0.55) !important; }',
                '& .xp-tw-a{ border:2px solid var(--tw-a) !important; }',
                '& .xp-tw-b{ border:2px solid var(--tw-b) !important; }',
                '& .xp-tw-a::before, & .xp-tw-b::before{',
                '  content:attr(data-xp-ab); position:absolute; z-index:40; top:8px; left:8px;',
                '  padding:3px 9px; border-radius:5px; pointer-events:none;',
                '  font:800 9.5px/1 ui-monospace,Menlo,Consolas,monospace; letter-spacing:1.6px; }',
                '& .xp-tw-a::before{ background:var(--tw-a); color:#04121c; }',
                '& .xp-tw-b::before{ background:var(--tw-b); color:#210a0f; }',

                /* flicker: B lifts onto A, identical geometry, instant swap */
                '&.xp-tw-flick .xp-tw-b{',
                '  position:absolute !important; z-index:80 !important;',
                '  left:var(--tw-ax,0) !important; top:0 !important;',
                '  transform:translateX(calc(-100% - 10px)) !important;',
                '  box-shadow:0 0 0 3px var(--tw-b), 0 20px 50px rgba(0,0,0,0.7) !important; }',
                '&.xp-tw-flick .xp-tw-a{ opacity:0 !important; }',

                '& .xp-tw-hint{ position:absolute; bottom:8px; left:14px; z-index:70;',
                '  font-size:10.5px; color:#5f7488; letter-spacing:0.3px; }',
                '& .xp-tw-hint b{ color:#9fb3c8; }',
                '& .xp-tw-hint kbd{ background:#1e2a36; color:#cfe2f2; border-radius:4px;',
                '  padding:1px 6px; font-family:ui-monospace,Menlo,Consolas,monospace; }',

                '& #splitViewContainer.xp-tw-sheet{ flex-direction:row !important;',
                '  align-items:stretch !important; }',
                '& .xp-tw-spine{ flex:0 0 auto !important; width:70px !important;',
                '  display:flex !important; flex-direction:column !important;',
                '  align-items:center !important; justify-content:center !important;',
                '  gap:8px !important; padding:8px 4px !important; min-height:0 !important;',
                '  background:#0e151c !important; border:1px solid #1e2a36 !important;',
                '  border-radius:8px !important; align-self:stretch !important; }',
                '& .xp-tw-spine #specChannelDock{ flex-direction:column !important; }',
                '& .xp-tw-spine .spec-channel-dock-cells{ flex-direction:column !important;',
                '  align-items:center !important; gap:8px !important; }',
                '& .xp-tw-strip{ flex:0 0 auto !important; gap:10px !important;',
                '  padding:6px 12px !important; min-height:0 !important; background:#0e151c !important;',
                '  border:1px solid #1e2a36 !important; border-radius:8px !important; }',
                '& .xp-tw-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:9px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-tw-strip .spec-channel-dock-cell{ background:#05080b !important;',
                '  border:1px solid #1e2a36 !important; border-radius:6px !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:linear-gradient(135deg,#38bdf8,#fb7185) !important;',
                '  color:#04121c !important; border:none !important; border-radius:8px !important;',
                '  font-weight:800 !important; letter-spacing:1.6px !important; padding:11px 26px !important;',
                '  animation:none !important; }',
                '& .vtool-btn{ border-radius:7px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(56,189,248,0.16) !important;',
                '  border-color:var(--tw-a) !important; color:var(--tw-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
