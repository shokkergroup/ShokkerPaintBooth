/* ============================================================================
 * EXPERIENCE 17 — ARCADE
 * Paradigm: PLAYFUL / REACTIVE. The app rewards you for doing things.
 *
 * The owner asked for "more fun to use". Every other experience answers that
 * with taste; Arcade answers it with FEEDBACK. Chunky saturated surfaces, hard
 * drop shadows that squash on press, and a live combo counter that reacts to
 * real actions (tool picks, zone selects, renders). Nothing about the workflow
 * changes — what changes is that the app acknowledges you.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '17-arcade',
        name: 'Arcade',
        tagline: 'Chunky, loud and reactive. The app cheers when you work.',
        paradigm: 'Playful reactive feedback',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // Cabinet layout: your roster sits along the BOTTOM like a
            // character-select strip, not down the side. Distinct from Pit Wall
            // (which puts its board on top) and frees the left edge entirely.

            // On a tall screen the roster is a bottom character-select strip.
            // On a SHORT one (1366x768) that band costs more height than the
            // pack can afford — trimmed as far as it would go it still measured
            // 246sq against Classic's 270sq. Rather than keep shaving, the
            // roster becomes a SIDE rail when vertical space is scarce: same
            // cards, same handlers, just re-hung where the room actually is.
            var leftRail = ctx.q('#leftPanel');
            var centerP = ctx.q('#centerPanel');
            var mainP = ctx.q('.main-container');
            if (leftRail && centerP && mainP) {
                var shortMq = window.matchMedia('(max-height: 860px)');
                var placeRoster = function () {
                    if (shortMq.matches) {
                        ctx.move(leftRail, mainP, { before: centerP });
                        leftRail.classList.remove('xp-ar-roster');
                        leftRail.classList.add('xp-ar-side');
                    } else {
                        ctx.move(leftRail, centerP);   // append = bottom
                        leftRail.classList.add('xp-ar-roster');
                        leftRail.classList.remove('xp-ar-side');
                    }
                    ctx.refit();
                };
                placeRoster();
                if (shortMq.addEventListener) shortMq.addEventListener('change', placeRoster);
                else if (shortMq.addListener) shortMq.addListener(placeRoster);
                ctx.onTeardown(function () {
                    try {
                        if (shortMq.removeEventListener) shortMq.removeEventListener('change', placeRoster);
                        else if (shortMq.removeListener) shortMq.removeListener(placeRoster);
                    } catch (_) {}
                    leftRail.classList.remove('xp-ar-roster', 'xp-ar-side');
                });
            }

            /* COMBO METER — reacts to real interactions, decays when you idle. */
            var hud = ctx.mk('div', { cls: 'xp-ar-hud', into: '#centerPanel' });
            var comboEl = ctx.mk('span', { cls: 'xp-ar-combo', text: 'READY' });
            var barEl = ctx.mk('span', { cls: 'xp-ar-bar' });
            var fill = ctx.mk('i', { cls: 'xp-ar-fill' });
            barEl.appendChild(fill);
            hud.appendChild(comboEl); hud.appendChild(barEl);

            var combo = 0, decay = null;
            var WORDS = ['READY', 'NICE', 'SHARP', 'ON FIRE', 'BLAZING', 'UNREAL'];
            function bump() {
                combo = Math.min(combo + 1, 30);
                var tier = Math.min(WORDS.length - 1, Math.floor(combo / 5));
                comboEl.textContent = combo > 1 ? WORDS[tier] + ' ×' + combo : WORDS[0];
                fill.style.width = Math.round((combo / 30) * 100) + '%';
                hud.classList.remove('pop'); void hud.offsetWidth; hud.classList.add('pop');
                clearTimeout(decay);
                decay = setTimeout(function () {
                    combo = 0; comboEl.textContent = 'READY'; fill.style.width = '0%';
                }, 5000);
            }
            ctx.on(document, 'click', function (e) {
                var t = e.target;
                if (!t || !t.closest) return;
                if (t.closest('.vtool-btn, .zone-card, .btn-render, .finish-item, .swatch-item')) bump();
            }, true);
            ctx.onTeardown(function () { clearTimeout(decay); });

            ctx.css([
                '&{ --xp-ch:54px; --xp-radius:16px;',
                '   --ar-1:#ff2e88; --ar-2:#00e5ff; --ar-3:#ffe600; --ar-ink:#12021f; }',
                '& #splitViewContainer{ padding:12px !important; gap:12px; }',
                '& .main-container{ background:',
                '  radial-gradient(900px 500px at 15% 0%, #2b0a52 0%, transparent 60%),',
                '  radial-gradient(800px 600px at 90% 100%, #06304a 0%, transparent 60%),',
                '  #120326 !important; }',
                '& #centerPanel, & #canvasViewport{ background:transparent !important; }',
                '& .header, & #spbTopToolbar{ background:#1b0637 !important;',
                '  border-bottom:4px solid #34095e !important; }',
                '& .right-panel{ background:#1b0637 !important; border-color:#34095e !important; }',
                '& #leftPanel.xp-ar-roster{',
                '  width:100% !important; min-width:0 !important; max-width:none !important;',
                '  flex:0 0 auto !important; height:auto !important; max-height:112px !important;',
                '  border-right:none !important; border-top:4px solid #34095e !important;',
                '  background:#1b0637 !important; overflow-y:auto !important; }',
                '& #leftPanel.xp-ar-roster #zoneList{ display:flex !important;',
                '  flex-direction:row !important; flex-wrap:wrap !important; gap:8px !important;',
                '  padding:8px !important; align-items:flex-start !important; }',
                '& #leftPanel.xp-ar-roster .zone-card{ flex:0 0 auto !important;',
                '  min-width:142px !important; margin:0 !important; }',
                /* short-screen form: the roster hangs down the left instead */
                '& #leftPanel.xp-ar-side{',
                '  width:196px !important; min-width:196px !important; max-width:196px !important;',
                '  height:auto !important; max-height:none !important;',
                '  border-top:none !important; border-right:4px solid #34095e !important;',
                '  background:#1b0637 !important; overflow-y:auto !important; }',

                /* chunky pressable everything */
                '& .btn, & .vtool-btn, & .zone-card, & .rp-tab{',
                '  background:#2a0a4f !important; color:#fff !important;',
                '  border:3px solid #12021f !important; border-radius:14px !important;',
                '  box-shadow:0 5px 0 #12021f !important; animation:none !important;',
                '  transition:transform .06s ease, box-shadow .06s ease !important; }',
                '& .btn:hover, & .vtool-btn:hover{ transform:translateY(-2px);',
                '  box-shadow:0 7px 0 #12021f !important; }',
                '& .btn:active, & .vtool-btn:active{ transform:translateY(4px);',
                '  box-shadow:0 1px 0 #12021f !important; }',
                '& .vtool-btn.active{ background:var(--ar-1) !important;',
                '  box-shadow:0 5px 0 #7a0d3f, 0 0 26px rgba(255,46,136,0.55) !important;',
                '  animation:none !important; }',
                '& .zone-card.selected, & .zone-card.active{ background:var(--ar-2) !important;',
                '  color:var(--ar-ink) !important; box-shadow:0 5px 0 #046b7d, 0 0 24px rgba(0,229,255,0.5) !important; }',
                '& .panel-header{ color:var(--ar-3) !important;',
                '  font-weight:900 !important; letter-spacing:1.6px !important;',
                '  text-shadow:2px 2px 0 #12021f !important; }',

                '& #splitSource, & #splitPreview{ background:#0a0116 !important;',
                '  border:4px solid var(--ar-3) !important; border-radius:16px !important;',
                '  box-shadow:0 8px 0 #12021f, 0 0 40px rgba(255,230,0,0.22) !important; }',
                '& .split-pane-label, & .preview-dual-label{ background:var(--ar-3) !important;',
                '  color:var(--ar-ink) !important; font-weight:900 !important;',
                '  letter-spacing:1.8px !important; border-radius:8px !important; border:none !important; }',

                '& .xp-ar-hud{ position:absolute; top:8px; right:14px; z-index:70;',
                '  display:flex; align-items:center; gap:9px; padding:6px 13px;',
                '  background:#2a0a4f; border:3px solid #12021f; border-radius:999px;',
                '  box-shadow:0 5px 0 #12021f; }',
                '& .xp-ar-hud.pop{ animation:xpArPop .26s cubic-bezier(.2,1.6,.3,1); }',
                '@keyframes xpArPop{ 0%{ transform:scale(1) } 45%{ transform:scale(1.14) } 100%{ transform:scale(1) } }',
                '& .xp-ar-combo{ font:900 12px/1 system-ui,sans-serif; color:var(--ar-3);',
                '  letter-spacing:1.4px; text-shadow:1.5px 1.5px 0 #12021f; min-width:82px; }',
                '& .xp-ar-bar{ display:block; width:74px; height:9px; border-radius:999px;',
                '  background:#12021f; overflow:hidden; }',
                '& .xp-ar-fill{ display:block; height:100%; width:0%; border-radius:999px;',
                '  background:linear-gradient(90deg,var(--ar-2),var(--ar-1),var(--ar-3));',
                '  transition:width .18s ease; }',

                '& .xp-ar-strip{ flex:0 0 auto !important; gap:12px !important;',
                '  padding:9px 14px !important; min-height:0 !important; background:#1b0637 !important;',
                '  border:3px solid #12021f !important; border-radius:16px !important;',
                '  box-shadow:0 5px 0 #12021f !important; }',
                '& .xp-ar-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:12px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-ar-strip .spec-channel-dock-cell{ background:#0a0116 !important;',
                '  border:3px solid #12021f !important; border-radius:11px !important;',
                '  box-shadow:0 4px 0 #12021f !important; }',
                '& .xp-ar-strip .spec-channel-dock-label{ background:var(--ar-2) !important;',
                '  color:var(--ar-ink) !important; font-weight:900 !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:10px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:linear-gradient(180deg,#ff5fa8,#ff2e88) !important; color:#fff !important;',
                '  border:3px solid #12021f !important; border-radius:16px !important;',
                '  font-size:15px !important; font-weight:900 !important; letter-spacing:2px !important;',
                '  padding:13px 34px !important;',
                '  box-shadow:0 6px 0 #7a0d3f, 0 0 30px rgba(255,46,136,0.5) !important;',
                '  animation:none !important; }',
                '& #previewBottomBar .btn-render:active{ transform:translateY(5px);',
                '  box-shadow:0 1px 0 #7a0d3f !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
