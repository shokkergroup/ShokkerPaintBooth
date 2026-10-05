/* ============================================================================
 * EXPERIENCE 05 — PIT WALL
 * Paradigm: TELEMETRY. Every value is a readout; the app is an engineer's stand.
 *
 * Where Studio hides information, Pit Wall surfaces it. This is an iRacing tool,
 * and race engineers do not hunt through menus — they read a wall of numbers and
 * act. A live status band reports zone count, layer count, selected zone, render
 * state and canvas zoom; RENDER becomes the start-light. Monospace throughout,
 * green-on-black, hard edges, zero decoration.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '05-pitwall',
        name: 'Pit Wall',
        tagline: 'Race-engineer telemetry. Everything is a readout.',
        paradigm: 'Telemetry dashboard',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            // A pit wall is a WALL, read left-to-right — not a sidebar. The
            // zones rail becomes a horizontal pit board above the artwork and
            // the left rail disappears entirely, which is what gives this
            // experience its own silhouette rather than another tinted variant.
            // The pit board is gone: the left rail now carries the ZONE POPOUT,
            // so relocating it put the inspector over the artwork. Pit Wall's
            // identity is the telemetry band, which lives in the rail instead.

            /* LIVE TELEMETRY BAND — real values read from the live DOM, polled
             * cheaply. Nothing here is decorative; every field maps to state the
             * owner otherwise has to go find. */
            var band = ctx.mk('div', {
                cls: 'xp-pit-band', into: '#leftPanel', first: true,
                attrs: { role: 'status', 'aria-live': 'off' }
            });
            var FIELDS = [
                { k: 'ZONES', get: function () { return document.querySelectorAll('#zoneList .zone-card').length; } },
                { k: 'ACTIVE', get: function () {
                    var s = document.querySelector('#zoneList .zone-card.selected, #zoneList .zone-card.active');
                    if (!s) return '--';
                    var n = s.querySelector('input, .zone-name');
                    return ((n && (n.value || n.textContent)) || '?').toString().slice(0, 10).toUpperCase();
                } },
                { k: 'LAYERS', get: function () { return document.querySelectorAll('.layer-row').length; } },
                { k: 'TOOL', get: function () {
                    var a = document.querySelector('.vtool-btn.active');
                    return a ? (a.getAttribute('aria-label') || a.id || '?').slice(0, 14).toUpperCase() : 'NONE';
                } },
                { k: 'ZOOM', get: function () {
                    var z = document.getElementById('zoomLevel');
                    return z ? (z.textContent || '').trim() : '--';
                } },
                { k: 'SERVER', get: function () {
                    var s = document.getElementById('serverStatus');
                    return s && s.classList.contains('offline') ? 'OFFLINE' : 'ONLINE';
                } }
            ];
            var cells = FIELDS.map(function (f) {
                var c = ctx.mk('div', { cls: 'xp-pit-cell' });
                var k = document.createElement('span'); k.className = 'xp-pit-k'; k.textContent = f.k;
                var v = document.createElement('span'); v.className = 'xp-pit-v'; v.textContent = '--';
                c.appendChild(k); c.appendChild(v);
                band.appendChild(c);
                return { f: f, v: v };
            });
            function tick() {
                cells.forEach(function (c) {
                    var nv;
                    try { nv = String(c.f.get()); } catch (_) { nv = '--'; }
                    if (nv !== c.v.textContent) {
                        c.v.textContent = nv;
                        c.v.classList.remove('flash');
                        void c.v.offsetWidth;          // restart the change flash
                        c.v.classList.add('flash');
                    }
                });
            }
            tick();
            var iv = setInterval(tick, 900);
            ctx.onTeardown(function () { clearInterval(iv); });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:0px; --pit-g:#39ff88; --pit-a:#ffcc33; --pit-dim:#4a6b58; }',
                '& #splitViewContainer{ padding:6px !important; gap:6px; }',

                '& .main-container, & #centerPanel, & #canvasViewport{ background:#050706 !important; }',
                '& .header{ background:#080b09 !important; border-bottom:1px solid #16301f !important; }',
                '& #spbTopToolbar{ background:#060907 !important; border-bottom:1px solid #16301f !important; }',
                '& .right-panel{ background:#070a08 !important; border-color:#16301f !important; }',
                '& #leftPanel.xp-pit-board{',
                '  width:100% !important; min-width:0 !important; max-width:none !important;',
                '  flex:0 0 auto !important; height:auto !important; max-height:128px !important;',
                '  border-right:none !important; border-bottom:1px solid #16301f !important;',
                '  background:#070a08 !important; overflow-y:auto !important; }',
                '& #leftPanel.xp-pit-board #zoneList{',
                '  display:flex !important; flex-direction:row !important; flex-wrap:wrap !important;',
                '  gap:6px !important; align-items:flex-start !important; padding:4px 8px !important; }',
                '& #leftPanel.xp-pit-board .zone-card{',
                '  flex:0 0 auto !important; min-width:128px !important; margin:0 !important; }',
                '& #leftPanel.xp-pit-board .panel-header{ padding:4px 10px !important; }',

                /* everything is a readout */
                '& .panel-header, & .rp-tab, & .vtool-label, & .section-header-label,',
                '& .zone-card, & .layer-row, & .split-pane-label, & .preview-dual-label{',
                '  font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace !important;',
                '  letter-spacing:0.6px !important; }',

                /* telemetry band */
                '& .xp-pit-band{',
                '  display:flex; flex-wrap:wrap; gap:1px; flex:0 0 auto;',
                '  background:#16301f; border-bottom:1px solid #16301f; }',
                '& .xp-pit-cell{',
                '  flex:1 1 120px; display:flex; align-items:baseline; gap:8px;',
                '  padding:5px 12px; background:#070a08; min-width:0; }',
                '& .xp-pit-k{ font:700 8px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  color:var(--pit-dim); letter-spacing:1.4px; }',
                '& .xp-pit-v{ font:700 13px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  color:var(--pit-g); letter-spacing:0.5px; overflow:hidden;',
                '  text-overflow:ellipsis; white-space:nowrap; }',
                '& .xp-pit-v.flash{ animation:xpPitFlash .5s ease-out; }',
                '@keyframes xpPitFlash{ 0%{ background:var(--pit-g); color:#050706; } 100%{ background:transparent; } }',

                /* screens, not cards */
                '& #splitSource, & #splitPreview{',
                '  background:#000 !important; border:1px solid #16301f !important;',
                '  border-radius:0 !important;',
                '  box-shadow:inset 0 0 60px rgba(57,255,136,0.05) !important; }',

                '& .xp-pit-bridge{',
                '  flex:0 0 auto !important; gap:10px !important; padding:6px 10px !important;',
                '  min-height:0 !important; background:#070a08 !important;',
                '  border:1px solid #16301f !important; border-radius:0 !important; }',
                '& .xp-pit-bridge #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:8px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-pit-bridge .spec-channel-dock-cell{ background:#000 !important;',
                '  border:1px solid #16301f !important; border-radius:0 !important; }',
                '& .xp-pit-bridge .spec-channel-dock-label{ background:#0a120d !important;',
                '  color:var(--pit-dim) !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',

                /* start light */
                '& #previewBottomBar .btn-render{',
                '  background:#0b1f13 !important; color:var(--pit-g) !important;',
                '  border:2px solid var(--pit-g) !important; border-radius:0 !important;',
                '  font:800 13px/1 ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:4px !important; padding:11px 26px !important;',
                '  box-shadow:0 0 0 1px #000, 0 0 22px rgba(57,255,136,0.45), inset 0 0 20px rgba(57,255,136,0.15) !important;',
                '  animation:none !important; }',

                '& .vtool-btn{ border-radius:0 !important; animation:none !important;',
                '  background:#0a0e0b !important; border:1px solid #16301f !important; }',
                '& .vtool-btn.active{ background:#0b1f13 !important; color:var(--pit-g) !important;',
                '  border-color:var(--pit-g) !important;',
                '  box-shadow:inset 0 0 14px rgba(57,255,136,0.25) !important; animation:none !important; }',
                '& .zone-card{ border-radius:0 !important; background:#0a0e0b !important;',
                '  border:1px solid #16301f !important; }',
                '& .zone-card.selected, & .zone-card.active{ border-color:var(--pit-a) !important;',
                '  box-shadow:inset 3px 0 0 var(--pit-a) !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
