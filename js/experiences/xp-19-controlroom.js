/* ============================================================================
 * EXPERIENCE 19 — CONTROL ROOM
 * Paradigm: EVERYTHING VISIBLE. The exact opposite of Zen.
 *
 * Zen shows one thing; Control Room shows all of them at once, as a wall of
 * live tiles. The four spec channels get promoted from a strip to full labelled
 * monitors with channel meaning spelled out (R = METALLIC, G = ROUGHNESS,
 * B = CLEARCOAT) — currently the single most confusing part of the app, because
 * B is inverted and nothing on screen says so. A status rail across the top
 * reports the whole system at a glance.
 *
 * For the painter who wants zero hidden state.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '19-controlroom',
        name: 'Control Room',
        tagline: 'A wall of live monitors. Channels labelled with what they mean.',
        paradigm: 'Everything-visible tile wall',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            // The fourth monitor column is gone: it made the strip a 1261x660
            // block beside the artwork and pushed the channels and RENDER
            // off-screen. Geometry belongs to the bench; Control Room's identity
            // is the labelled channel meanings and the live status rail.

            /* Spell out what each channel actually controls. This is real
             * knowledge from the codebase (B is inverted: 16 = max gloss) that
             * the UI has never surfaced. */
            var MEANING = {
                all: 'COMPOSITE',
                r: 'R · METALLIC — 0 dielectric → 255 metal',
                g: 'G · ROUGHNESS — 0 mirror → 255 matte',
                b: 'B · CLEARCOAT — 16 max gloss → 255 dull'
            };
            // Captions INSIDE the cells widened them until all four ran off-screen
            // at 1366px. The knowledge is what matters, not its position, so it
            // becomes a legend line under the status rail — still always visible,
            // and the squares stay small and square.
            var legend = ctx.mk('div', {
                cls: 'xp-cr-legend',
                text: MEANING.r + '   ·   ' + MEANING.g + '   ·   ' + MEANING.b
            });

            /* Status rail — the system at a glance, no hunting. */
            var rail = ctx.mk('div', { cls: 'xp-cr-rail', into: '#leftPanel', first: true });
            var FIELDS = [
                ['ZONES', function () { return document.querySelectorAll('#zoneList .zone-card').length; }],
                ['LAYERS', function () { return document.querySelectorAll('.layer-row').length; }],
                ['TOOL', function () {
                    var a = document.querySelector('.vtool-btn.active');
                    return a ? (a.getAttribute('aria-label') || '?').slice(0, 16) : '—';
                }],
                ['ZOOM', function () {
                    var z = document.getElementById('zoomLevel');
                    return z ? (z.textContent || '').trim() : '—';
                }],
                ['CANVAS', function () { return '2048²'; }],
                ['LINK', function () {
                    var s = document.getElementById('serverStatus');
                    return s && s.classList.contains('offline') ? 'OFFLINE' : 'ONLINE';
                }]
            ];
            var cells = FIELDS.map(function (f) {
                var c = ctx.mk('div', { cls: 'xp-cr-cell' });
                var k = document.createElement('b'); k.textContent = f[0];
                var v = document.createElement('span'); v.textContent = '—';
                c.appendChild(k); c.appendChild(v);
                rail.appendChild(c);
                return { get: f[1], v: v };
            });
            function tick() {
                cells.forEach(function (c) {
                    var s; try { s = String(c.get()); } catch (_) { s = '—'; }
                    if (c.v.textContent !== s) c.v.textContent = s;
                });
            }
            if (legend && rail && rail.parentElement) rail.parentElement.insertBefore(legend, rail.nextSibling);
            tick();
            var iv = setInterval(tick, 1000);
            ctx.onTeardown(function () { clearInterval(iv); });

            ctx.css([
                '&{ --xp-ch:64px; --xp-radius:4px; --cr-a:#5eead4; --cr-line:#1c2b30; }',
                '& #splitViewContainer{ padding:6px !important; gap:6px; }',
                '& .main-container, & #centerPanel{ background:#070d0f !important; }',
                '& .header, & #spbTopToolbar{ background:#0a1416 !important;',
                '  border-bottom:1px solid var(--cr-line) !important; }',
                '& .left-panel, & .right-panel{ background:#0a1416 !important;',
                '  border-color:var(--cr-line) !important; }',

                /* status rail */
                '& .xp-cr-rail{ flex:0 0 auto; display:flex; gap:1px; background:var(--cr-line);',
                '  border-bottom:1px solid var(--cr-line); }',
                '& .xp-cr-cell{ flex:1 1 0; display:flex; align-items:baseline; gap:7px;',
                '  padding:5px 11px; background:#0a1416; min-width:0; }',
                '& .xp-cr-cell b{ font:700 8px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  color:#4d6b70; letter-spacing:1.3px; }',
                '& .xp-cr-cell span{ font:700 12px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  color:var(--cr-a); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }',

                /* monitors */
                '& #splitSource, & #splitPreview{ background:#000 !important;',
                '  border:1px solid var(--cr-line) !important; border-radius:4px !important;',
                '  box-shadow:inset 0 0 40px rgba(94,234,212,0.05) !important; }',
                '& .split-pane-label, & .preview-dual-label{ background:#0a1416 !important;',
                '  color:var(--cr-a) !important; border:1px solid var(--cr-line) !important;',
                '  border-radius:3px !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:2px !important; }',

                /* the channel wall — promoted from thumbnails to monitors */
                /* The 96px monitor column pushed the channels off-screen at 1366px
                   (measured x=1478 on a 1366 viewport). Geometry belongs to the
                   bench; only the monitor LOOK is Control Room's. */
                '& .spbx-bench-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:8px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .spbx-bench-strip .spec-channel-dock-cell{ background:#000 !important;',
                '  border:1px solid var(--cr-line) !important; border-radius:3px !important;',
                '  width:auto !important; min-width:var(--xp-ch) !important; }',
                '& .spbx-bench-strip .spec-channel-dock-label{ background:#0d1b1e !important;',
                '  color:var(--cr-a) !important;',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important; }',
                '& .xp-cr-legend{ padding:4px 8px; font:600 7.5px/1.5 ui-monospace,Menlo,Consolas,monospace;',
                '  color:#4d6b70; letter-spacing:0.2px; border-bottom:1px solid var(--cr-line);',
                '  background:#0a1416; }',
                '& .xp-cr-cap{ padding:2px 4px 3px; max-width:150px;',
                '  font:600 6.5px/1.35 ui-monospace,Menlo,Consolas,monospace;',
                '  color:#4d6b70; letter-spacing:0.2px; text-align:center;',
                '  border-top:1px solid var(--cr-line); }',

                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:#0c2b28 !important; color:var(--cr-a) !important;',
                '  border:1px solid var(--cr-a) !important; border-radius:3px !important;',
                '  font:800 12px/1 ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:2.6px !important; padding:11px 26px !important;',
                '  box-shadow:0 0 18px rgba(94,234,212,0.3) !important; animation:none !important; }',
                '& .vtool-btn{ border-radius:3px !important; animation:none !important;',
                '  background:#0c1618 !important; border:1px solid var(--cr-line) !important; }',
                '& .vtool-btn.active{ background:#0c2b28 !important; color:var(--cr-a) !important;',
                '  border-color:var(--cr-a) !important; box-shadow:none !important; animation:none !important; }',
                '& .zone-card{ border-radius:3px !important; background:#0c1618 !important;',
                '  border:1px solid var(--cr-line) !important; }',
                '& .zone-card.selected, & .zone-card.active{ border-color:var(--cr-a) !important;',
                '  box-shadow:inset 3px 0 0 var(--cr-a) !important; }',
                '& .panel-header, & .rp-tab, & .section-header-label{',
                '  font-family:ui-monospace,Menlo,Consolas,monospace !important;',
                '  letter-spacing:1.2px !important; color:#7fb3ad !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
