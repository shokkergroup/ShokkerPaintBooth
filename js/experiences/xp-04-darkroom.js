/* ============================================================================
 * EXPERIENCE 04 — DARKROOM
 * Paradigm: COMPARE-FIRST. Two prints on a light table, under a loupe.
 *
 * The job you actually do in this app is comparing: does the LIVE PREVIEW match
 * what I wanted when I changed the SOURCE? Darkroom makes that the whole UI.
 * The surround goes near-black safelight red so the only bright things on
 * screen are the two prints; a real magnifier loupe follows the cursor over
 * either box; and the four spec channels become a contact-sheet filmstrip.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '04-darkroom',
        name: 'Darkroom',
        tagline: 'Two prints on a light table. Loupe follows your cursor.',
        paradigm: 'Compare-first + magnifier',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            /* THE LOUPE — a real magnifier over whichever box you are on.
             * It samples the live <canvas>/<img> by scaling a cloned CSS
             * background, so it magnifies whatever is genuinely rendered. */
            var loupe = ctx.mk('div', { cls: 'xp-dark-loupe', into: 'body' });
            var lens = ctx.mk('div', { cls: 'xp-dark-lens' });
            loupe.appendChild(lens);
            var ZOOM = 3.2, SIZE = 190;
            var raf = null, on = false;

            function place(e) {
                var box = e.target && e.target.closest
                    ? e.target.closest('#splitSource, #splitPreview') : null;
                if (!box) { hide(); return; }
                var media = box.querySelector('canvas, img');
                if (!media) { hide(); return; }
                var r = media.getBoundingClientRect();
                if (r.width < 4 || e.clientX < r.left || e.clientX > r.right ||
                    e.clientY < r.top || e.clientY > r.bottom) { hide(); return; }
                if (raf) cancelAnimationFrame(raf);
                raf = requestAnimationFrame(function () {
                    var src = media.tagName === 'IMG' ? media.src : null;
                    if (media.tagName === 'CANVAS') {
                        try { src = media.toDataURL(); } catch (_) { src = null; }
                    }
                    if (!src) { hide(); return; }
                    var fx = (e.clientX - r.left) / r.width;
                    var fy = (e.clientY - r.top) / r.height;
                    lens.style.backgroundImage = 'url(' + src + ')';
                    lens.style.backgroundSize = (r.width * ZOOM) + 'px ' + (r.height * ZOOM) + 'px';
                    lens.style.backgroundPosition =
                        (-(fx * r.width * ZOOM) + SIZE / 2) + 'px ' +
                        (-(fy * r.height * ZOOM) + SIZE / 2) + 'px';
                    loupe.style.left = (e.clientX + 22) + 'px';
                    loupe.style.top = (e.clientY - SIZE - 10) + 'px';
                    if (!on) { loupe.classList.add('on'); on = true; }
                });
            }
            function hide() { if (on) { loupe.classList.remove('on'); on = false; } }

            // Canvas toDataURL on every mousemove would be brutal; only run the
            // loupe while the owner holds Alt (the classic "inspect" modifier).
            ctx.on(document, 'mousemove', function (e) { if (e.altKey) place(e); else hide(); });
            ctx.on(document, 'keyup', function (e) { if (e.key === 'Alt') hide(); });
            ctx.onTeardown(function () { if (raf) cancelAnimationFrame(raf); });

            var hint = ctx.mk('div', {
                cls: 'xp-dark-hint', into: '#centerPanel',
                html: 'Hold <kbd>Alt</kbd> over either print for the loupe'
            });
            void hint;

            ctx.css([
                '&{ --xp-ch:50px; --xp-radius:3px; --dk-safe:#c2412d; --dk-paper:#f3ede2; }',
                '& #splitViewContainer{ padding:14px !important; gap:14px; }',

                /* safelight surround */
                '& .main-container, & #centerPanel, & #canvasViewport{',
                '  background:radial-gradient(circle at 50% 30%, #1a0d0b 0%, #0a0605 70%) !important; }',
                '& .header{ background:#120908 !important; border-bottom:1px solid #331512 !important; }',
                '& #spbTopToolbar{ background:#0d0706 !important; border-bottom:1px solid #331512 !important; }',
                '& .left-panel, & .right-panel{ background:#100907 !important; border-color:#2b1310 !important; }',

                /* the two prints — the only bright things on screen */
                '& #splitSource, & #splitPreview{',
                '  background:#000 !important;',
                '  border:10px solid var(--dk-paper) !important;',
                '  border-radius:2px !important;',
                '  box-shadow:0 24px 60px rgba(0,0,0,0.85), 0 0 0 1px rgba(0,0,0,0.6) !important;',
                '}',
                '& .split-pane-label, & .preview-dual-label{',
                '  background:var(--dk-paper) !important; color:#1a1a1a !important;',
                '  font:700 9px/1.6 Georgia,serif !important; letter-spacing:2px !important;',
                '}',

                /* contact sheet */
                '& .xp-dark-sheet{',
                '  flex:0 0 auto !important; justify-content:center !important;',
                '  gap:16px !important; padding:8px 14px !important; min-height:0 !important;',
                '  background:rgba(0,0,0,0.55) !important;',
                '  border:1px solid #2b1310 !important; border-radius:3px !important;',
                '}',
                '& .xp-dark-sheet #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:14px !important; }',
                '& .xp-dark-sheet .spec-channel-dock-cell{',
                '  background:#000 !important; border:4px solid var(--dk-paper) !important;',
                '  border-radius:1px !important; box-shadow:0 6px 16px rgba(0,0,0,0.7) !important; }',
                '& .xp-dark-sheet .spec-channel-dock-label{',
                '  background:var(--dk-paper) !important; color:#222 !important;',
                '  font-family:Georgia,serif !important; }',
                '& #previewBottomBar.spbx-relocated{',
                '  background:transparent !important; border:none !important; padding:0 !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:var(--dk-safe) !important; color:#fff !important; border:none !important;',
                '  font:700 12px/1 Georgia,serif !important; letter-spacing:3px !important;',
                '  padding:11px 26px !important; border-radius:2px !important; animation:none !important;',
                '  box-shadow:0 0 24px rgba(194,65,45,0.5) !important; }',

                /* loupe */
                '& .xp-dark-loupe{',
                '  position:fixed; z-index:9500; width:190px; height:190px;',
                '  border-radius:50%; pointer-events:none; opacity:0;',
                '  border:6px solid var(--dk-paper);',
                '  box-shadow:0 18px 44px rgba(0,0,0,0.8), inset 0 0 30px rgba(0,0,0,0.5);',
                '  transition:opacity .12s ease; overflow:hidden; }',
                '& .xp-dark-loupe.on{ opacity:1; }',
                '& .xp-dark-lens{ position:absolute; inset:0; border-radius:50%;',
                '  background-repeat:no-repeat; image-rendering:pixelated; }',
                '& .xp-dark-hint{',
                '  position:absolute; bottom:8px; left:14px; z-index:70;',
                '  font:400 10px/1 Georgia,serif; color:#8a5a50; letter-spacing:0.6px; }',
                '& .xp-dark-hint kbd{ color:var(--dk-paper); border:1px solid #4a231e;',
                '  border-radius:3px; padding:1px 5px; }',

                '& .vtool-btn{ border-radius:2px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(194,65,45,0.2) !important;',
                '  border-color:var(--dk-safe) !important; color:#f0a596 !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
