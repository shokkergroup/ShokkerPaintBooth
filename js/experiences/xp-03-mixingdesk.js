/* ============================================================================
 * EXPERIENCE 03 — MIXING DESK
 * Paradigm: CHANNEL STRIPS. The app becomes an audio console.
 *
 * Why this metaphor earns its place (it is not decoration):
 *   A paint recipe IS a mix. You have N zones, each contributing to one output,
 *   each with a level, a mute, a solo, and a stack of processing. Engineers
 *   solved "many parallel contributors, one output" decades ago — the channel
 *   strip. Zones become numbered strips, every slider becomes a fader, the
 *   selected zone's inspector becomes the wide strip on the right, and the four
 *   spec channels become a METER BRIDGE across the bottom with RENDER as the
 *   transport button.
 *
 * Geometry: the meter bridge lives in the spare height BELOW the artwork (the
 * squares are width-limited, so vertical space down there is free). The four
 * channel previews stay small and perfectly square — they read as VU meters,
 * which is exactly what a square 2048x2048 preview wants to be.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '03-mixingdesk',
        name: 'Mixing Desk',
        tagline: 'Zones are channel strips. Spec channels are the meter bridge.',
        paradigm: 'Channel strips / console',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            /* 1. Width back to the artwork; the zone inspector becomes the
             *    selected channel's strip on the right of the desk. */

            /* 2. METER BRIDGE — the four spec channels plus the transport,
             *    below the artwork where the height is free. */
            var container = ctx.q('#splitViewContainer');
            var strip = ctx.q('#previewTopStrip');
            var bottomBar = ctx.q('#previewBottomBar');
            if (container && strip) {
                ctx.move(strip, container);            // append = below the squares
                ctx.addClass(strip, 'xp-desk-bridge');
                // The transport (RENDER + region actions + zoom) joins the bridge
                // so the whole console reads as one hardware surface.
                if (bottomBar) {
                    ctx.move(bottomBar, strip);
                    // spbx-relocated releases the id-pinned 76px height/flex from
                    // the inline simplify block — without it the bar becomes a
                    // 76x76 box and RENDER spills out over the artwork.
                    ctx.addClass(bottomBar, 'spbx-relocated');
                    ctx.addClass(bottomBar, 'xp-desk-transport');
                }
            }

            // Tool options float over the canvas — on a desk these are the
            // "currently patched processor" controls, not a permanent band.
            var opts = ctx.q('#toolOptionsBar');
            if (opts) {
                ctx.addClass(opts, 'spbx-float');
                ctx.addClass(opts, 'spbx-float-top');
                ctx.addClass(opts, 'xp-desk-hud');
            }

            /* 3. CHANNEL NUMBERING — give every zone strip a console channel
             *    label. Re-applied on zone re-render because the app rebuilds
             *    the list's innerHTML whenever zones change. */
            // [FIX 2026-08-05] This was an INFINITE LOOP that killed the renderer.
            // numberStrips() writes into #zoneList, and the MutationObserver below
            // watches #zoneList with subtree:true — so appending the label (or even
            // re-assigning identical textContent, which still replaces the text
            // node) re-fired the observer, which called numberStrips again, for
            // ever. MutationObserver callbacks are microtasks, so this starves the
            // event loop: the tab hangs and the renderer dies.
            //
            // Why it hid for a week: the capture gate applies a pack and MEASURES
            // it, never mutating the zone list. Only clicking a zone card (which
            // makes the app rebuild #zoneList) triggers it — and the functional
            // smoke had been run with --only 01 since. The first full 21-state run
            // hit it immediately.
            //
            // Two guards, either of which alone would fix it; both because this
            // class of bug is silent until it is fatal:
            //   1. the observer is DISCONNECTED while we mutate, then reconnected
            //   2. text is only written when it actually differs
            var mo = null;
            function numberStrips() {
                if (mo) { try { mo.disconnect(); } catch (_) {} }
                try {
                    var cards = document.querySelectorAll('#leftPanel .zone-card');
                    for (var i = 0; i < cards.length; i++) {
                        var card = cards[i];
                        var label = card.querySelector(':scope > .xp-desk-ch');
                        if (!label) {
                            label = document.createElement('span');
                            label.className = 'xp-desk-ch';
                            label.setAttribute('aria-hidden', 'true');
                            card.appendChild(label);
                        }
                        var want = 'CH ' + (i + 1);
                        if (label.textContent !== want) label.textContent = want;
                    }
                } finally {
                    if (mo && zoneList) {
                        try { mo.observe(zoneList, { childList: true, subtree: true }); } catch (_) {}
                    }
                }
            }
            var zoneList = ctx.q('#zoneList');
            numberStrips();
            if (zoneList) {
                mo = new MutationObserver(function () { numberStrips(); });
                mo.observe(zoneList, { childList: true, subtree: true });
                ctx.onTeardown(function () {
                    try { mo.disconnect(); } catch (_) {}
                    document.querySelectorAll('.xp-desk-ch').forEach(function (el) {
                        if (el.parentNode) el.parentNode.removeChild(el);
                    });
                });
            }

            /* 4. THE CONSOLE LANGUAGE
             * Brushed dark metal, screen-printed labels, LED accents, and every
             * range input rebuilt as a fader with a chunky cap. */
            ctx.css([
                '&{ --xp-ch:56px; --xp-radius:4px;',
                '   --desk-accent:#f0b429; --desk-led:#4ade80; --desk-metal:#1a1c1f;',
                '   --desk-slot:#0b0c0e; }',

                '& #splitViewContainer{ padding:8px !important; gap:8px; }',

                /* --- the desk surface --- */
                '& .main-container, & #centerPanel{',
                '  background:linear-gradient(180deg,#17191c,#101113) !important;',
                '}',
                '& .left-panel, & .right-panel{',
                '  background:linear-gradient(180deg,#1d1f23,#141518) !important;',
                '  border-color:#000 !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.06) !important;',
                '}',
                '& .header{ background:linear-gradient(180deg,#212429,#141619) !important;',
                '  border-bottom:2px solid #000 !important; }',
                '& #spbTopToolbar{ background:#15171a !important; border-bottom:2px solid #000 !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.05) !important; }',

                /* --- zone rows become channel strips --- */
                '& #leftPanel .zone-card{',
                '  position:relative !important;',
                '  background:linear-gradient(180deg,#212429,#17191d) !important;',
                '  border:1px solid #000 !important; border-radius:3px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.07), 0 2px 4px rgba(0,0,0,0.5) !important;',
                '  padding-left:34px !important;',
                '}',
                /* Screen-printed channel number. A CHILD element, deliberately —
                   .zone-card::before is the app's own zone-colour accent stripe and
                   must survive. This sits just inboard of it. */
                '& #leftPanel .zone-card > .xp-desk-ch{',
                '  position:absolute; left:6px; top:0; bottom:0; width:22px;',
                '  display:flex; align-items:center; justify-content:center;',
                '  writing-mode:vertical-rl; transform:rotate(180deg);',
                '  font:700 8px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  letter-spacing:1.2px; color:#0c0d0f;',
                '  background:linear-gradient(180deg,var(--desk-accent),#c98f10);',
                '  border-left:1px solid #000; border-right:1px solid #000;',
                '  z-index:6; pointer-events:none;',
                '}',
                '& #leftPanel .zone-card.selected, & #leftPanel .zone-card.active{',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.12), 0 0 0 1px var(--desk-led),',
                '              0 0 14px rgba(74,222,128,0.28) !important;',
                '}',

                /* --- every slider becomes a fader --- */
                '& input[type="range"]{',
                '  -webkit-appearance:none; appearance:none;',
                '  height:20px !important; background:transparent !important;',
                '}',
                '& input[type="range"]::-webkit-slider-runnable-track{',
                '  height:6px; border-radius:2px;',
                '  background:linear-gradient(180deg,var(--desk-slot),#000);',
                '  box-shadow:inset 0 1px 2px rgba(0,0,0,0.9), 0 1px 0 rgba(255,255,255,0.06);',
                '}',
                '& input[type="range"]::-webkit-slider-thumb{',
                '  -webkit-appearance:none; appearance:none;',
                '  width:14px; height:20px; margin-top:-7px; border-radius:2px;',
                '  background:linear-gradient(180deg,#4a4f57,#22252a);',
                '  border:1px solid #000;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.35), 0 2px 4px rgba(0,0,0,0.7);',
                '}',
                '& input[type="range"]:hover::-webkit-slider-thumb{',
                '  background:linear-gradient(180deg,#5b616b,#2a2e34);',
                '}',
                /* the cap gets a centre line, like a real fader */
                '& input[type="range"]::-moz-range-thumb{',
                '  width:14px; height:20px; border-radius:2px; border:1px solid #000;',
                '  background:linear-gradient(180deg,#4a4f57,#22252a);',
                '}',

                /* --- meter bridge --- */
                '& .xp-desk-bridge{',
                '  flex:0 0 auto !important; display:flex !important;',
                '  align-items:center !important; justify-content:space-between !important;',
                '  gap:14px !important; padding:8px 12px !important; min-height:0 !important;',
                '  background:linear-gradient(180deg,#212429,#131417) !important;',
                '  border:1px solid #000 !important; border-radius:5px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.08), 0 3px 8px rgba(0,0,0,0.55) !important;',
                '}',
                '& .xp-desk-bridge #specChannelDock{',
                '  background:transparent !important; border:none !important;',
                '  padding:0 !important; gap:10px !important; flex:0 0 auto !important;',
                '  justify-content:flex-start !important;',
                '}',
                '& .xp-desk-bridge .spec-channel-dock-cell{',
                '  background:#000 !important;',
                '  border:1px solid #33383f !important; border-radius:3px !important;',
                '  box-shadow:inset 0 0 10px rgba(0,0,0,0.9), 0 1px 0 rgba(255,255,255,0.06) !important;',
                '}',
                '& .xp-desk-bridge .spec-channel-dock-label{',
                '  background:#0d0e10 !important; color:var(--desk-accent) !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  border-bottom:1px solid #000 !important;',
                '}',
                '& .xp-desk-bridge .spec-channel-dock-cell:hover{ border-color:var(--desk-accent) !important; }',

                /* --- transport --- */
                '& #previewBottomBar.xp-desk-transport{',
                '  flex:1 1 auto !important; height:auto !important;',
                '  min-height:0 !important; max-height:none !important;',
                '  display:flex !important; align-items:center !important;',
                '  justify-content:flex-end !important; gap:8px !important;',
                '  background:transparent !important; border:none !important;',
                '  padding:0 !important;',
                '}',
                '& #previewBottomBar.xp-desk-transport .btn-render{',
                '  background:linear-gradient(180deg,#f5c445,#c4890c) !important;',
                '  color:#1a1200 !important;',
                '  border:1px solid #000 !important; border-radius:4px !important;',
                '  font:800 13px/1 ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:2px !important; padding:12px 30px !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.5), 0 3px 0 #6b4a05,',
                '              0 0 22px rgba(240,180,41,0.4) !important;',
                '  animation:none !important;',
                '}',
                '& #previewBottomBar.xp-desk-transport .btn-render:active{',
                '  transform:translateY(2px);',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.35), 0 1px 0 #6b4a05 !important;',
                '}',

                /* --- artwork wells are recessed into the desk --- */
                '& #splitSource, & #splitPreview{',
                '  background:#000 !important;',
                '  border:1px solid #000 !important; border-radius:4px !important;',
                '  box-shadow:inset 0 0 0 1px rgba(255,255,255,0.06),',
                '              inset 0 2px 12px rgba(0,0,0,0.9), 0 2px 6px rgba(0,0,0,0.6) !important;',
                '}',

                /* --- console typography: labels are screen-printed --- */
                '& .panel-header, & .rp-tab, & .vtool-label, & .section-header-label{',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:1.1px !important; text-transform:uppercase !important;',
                '}',
                '& .vtool-btn{ border-radius:3px !important; animation:none !important;',
                '  background:linear-gradient(180deg,#24272c,#181a1d) !important;',
                '  border:1px solid #000 !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.08) !important; }',
                '& .vtool-btn.active{',
                '  background:linear-gradient(180deg,#3a3202,#241f01) !important;',
                '  border-color:var(--desk-accent) !important; color:var(--desk-accent) !important;',
                '  box-shadow:inset 0 1px 0 rgba(255,255,255,0.1), 0 0 10px rgba(240,180,41,0.35) !important;',
                '}',
                '& .xp-desk-hud{ padding:4px 10px !important; height:auto !important;',
                '  background:rgba(20,22,25,0.95) !important; border:1px solid #000 !important; }',

                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
