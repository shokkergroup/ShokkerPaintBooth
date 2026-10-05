/* ============================================================================
 * EXPERIENCE 09 — STAGES
 * Paradigm: LINEAR GUIDED. One job at a time, with a spine that shows where
 * you are in the job.
 *
 * The app currently shows everything at once, which is why it reads as complex.
 * Stages keeps every panel mounted (nothing is removed, nothing is unreachable)
 * but SPOTLIGHTS one step at a time: SOURCE -> ZONES -> FINISH -> SPEC -> RENDER.
 * The other panels stay visible and clickable, they simply recede — so a new
 * user is told where to look, and an expert can ignore the spine entirely.
 *
 * This is the "accessible without stripping features" case in its purest form.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '09-stages',
        name: 'Stages',
        tagline: 'Source → Zones → Finish → Spec → Render. One step lit at a time.',
        paradigm: 'Linear guided spine',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // A workflow spine belongs beside the work, running top to bottom —
            // a horizontal strip above the canvas reads as one more toolbar and
            // looked like every other pack. Vertical is the whole silhouette.

            ctx.addClass(document.body, 'xp-st-vertical');

            var STEPS = [
                { id: 'source', n: '1', label: 'SOURCE', hint: 'Load the car you are painting',
                  lit: ['.header'] },
                { id: 'zones', n: '2', label: 'ZONES', hint: 'Claim the pixels each colour owns',
                  lit: ['#leftPanel'] },
                { id: 'finish', n: '3', label: 'FINISH', hint: 'Choose a base and a pattern',
                  lit: ['#rightPanel'] },
                { id: 'spec', n: '4', label: 'SPEC', hint: 'Check metal, rough and clearcoat',
                  lit: ['#previewTopStrip'] },
                { id: 'render', n: '5', label: 'RENDER', hint: 'Write the TGAs for iRacing',
                  lit: ['#previewBottomBar'] }
            ];

            var spine = ctx.mk('div', {
                cls: 'xp-st-spine spbx-scroll-y',
                attrs: { role: 'tablist', 'aria-label': 'Workflow stages' }
            });
            var mainS = ctx.q('.main-container');
            var centerS = ctx.q('#centerPanel');
            if (mainS && centerS) mainS.insertBefore(spine, centerS);
            var hint = ctx.mk('div', { cls: 'xp-st-hint', into: '#centerPanel' });

            var current = null, litNodes = [];
            function light(step) {
                litNodes.forEach(function (n) { n.classList.remove('xp-st-lit'); });
                litNodes = [];
                document.body.classList.add('xp-st-focus');
                step.lit.forEach(function (sel) {
                    document.querySelectorAll(sel).forEach(function (n) {
                        n.classList.add('xp-st-lit');
                        litNodes.push(n);
                    });
                });
                spine.querySelectorAll('.xp-st-step').forEach(function (b) {
                    var on = b.getAttribute('data-step') === step.id;
                    b.classList.toggle('on', on);
                    b.setAttribute('aria-selected', on ? 'true' : 'false');
                });
                hint.textContent = step.hint;
                current = step.id;
            }
            ctx.onTeardown(function () {
                document.body.classList.remove('xp-st-focus');
                document.querySelectorAll('.xp-st-lit').forEach(function (n) {
                    n.classList.remove('xp-st-lit');
                });
            });

            STEPS.forEach(function (s) {
                var b = ctx.mk('button', {
                    cls: 'xp-st-step',
                    attrs: { type: 'button', role: 'tab', 'data-step': s.id, 'aria-selected': 'false' },
                    html: '<span class="xp-st-n">' + s.n + '</span><span class="xp-st-l">' + s.label + '</span>'
                });
                spine.appendChild(b);
                ctx.on(b, 'click', function () { light(s); });
            });
            light(STEPS[1]);   // land on ZONES: step 1 is already done by boot

            // Advancing with the keyboard makes the spine feel like a real flow.
            ctx.on(document, 'keydown', function (e) {
                if (!e.altKey) return;
                var i = STEPS.findIndex(function (s) { return s.id === current; });
                if (e.key === 'ArrowRight') { e.preventDefault(); light(STEPS[(i + 1) % STEPS.length]); }
                if (e.key === 'ArrowLeft') { e.preventDefault(); light(STEPS[(i - 1 + STEPS.length) % STEPS.length]); }
            });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:8px; --st-a:#38bdf8; --st-done:#22c55e; }',
                '& #splitViewContainer{ padding:8px !important; gap:8px; }',
                '& .main-container, & #centerPanel{ background:#0b1118 !important; }',
                '& .header, & #spbTopToolbar{ background:#0d141d !important;',
                '  border-bottom:1px solid #1d2937 !important; }',
                '& .left-panel, & .right-panel{ background:#0d141d !important; border-color:#1d2937 !important; }',

                /* the spine */
                '& .xp-st-spine{ display:flex; flex-direction:column; align-items:stretch; gap:0;',
                '  flex:0 0 146px; width:146px; padding:10px 0;',
                '  background:#0d141d; border-right:1px solid #1d2937; }',
                '& .xp-st-step{ flex:0 0 auto; display:flex; align-items:center; justify-content:flex-start;',
                '  gap:10px; padding:13px 14px; cursor:pointer; position:relative;',
                '  background:transparent; border:none; border-left:3px solid transparent;',
                '  border-bottom:none; text-align:left;',
                '  color:#5b6b7d; font-size:11.5px; font-weight:700; letter-spacing:1.4px; }',
                '& .xp-st-step:hover{ color:#9fb3c8; }',
                '& .xp-st-step.on{ color:#fff; border-left-color:var(--st-a);',
                '  background:linear-gradient(90deg,rgba(56,189,248,0.14),transparent); }',
                '& .xp-st-n{ width:20px; height:20px; border-radius:50%; flex:0 0 auto;',
                '  display:flex; align-items:center; justify-content:center;',
                '  background:#1d2937; color:#8aa0b6; font-size:10px; }',
                '& .xp-st-step.on .xp-st-n{ background:var(--st-a); color:#04121c; }',
                /* connector chevrons between steps */
                /* connector runs downward between the steps */
                '& .xp-st-step + .xp-st-step::before{ content:""; position:absolute; left:50%; top:-5px;',
                '  width:7px; height:7px; margin-left:-4px;',
                '  border-right:1px solid #1d2937; border-bottom:1px solid #1d2937;',
                '  transform:rotate(45deg); }',
                '& .xp-st-hint{ flex:0 0 auto; padding:5px 14px; font-size:11px; color:#7d93a8;',
                '  background:#0b1118; border-bottom:1px solid #1d2937; letter-spacing:0.3px; }',

                /* spotlight: unlit chrome recedes but stays fully usable */
                '&.xp-st-focus .left-panel, &.xp-st-focus .right-panel,',
                '&.xp-st-focus #previewTopStrip, &.xp-st-focus #previewBottomBar,',
                '&.xp-st-focus .header{',
                '  opacity:0.55; transition:opacity .2s ease, box-shadow .2s ease; }',
                '&.xp-st-focus .xp-st-lit{',
                '  opacity:1 !important;',
                '  box-shadow:0 0 0 2px var(--st-a), 0 0 26px rgba(56,189,248,0.28) !important;',
                '  z-index:60; position:relative; }',
                '&.xp-st-focus .left-panel:hover, &.xp-st-focus .right-panel:hover,',
                '&.xp-st-focus .header:hover{ opacity:1; }',

                '& #splitSource, & #splitPreview{ background:#060a0f !important;',
                '  border:1px solid #1d2937 !important; border-radius:10px !important;',
                '  box-shadow:0 14px 36px rgba(0,0,0,0.5) !important; }',
                '& #previewTopStrip{ flex:0 0 auto !important; padding:5px 10px !important;',
                '  min-height:0 !important; background:#0d141d !important;',
                '  border:1px solid #1d2937 !important; border-radius:8px !important;',
                '  gap:10px !important; }',
                '& #previewTopStrip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:8px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{',
                '  background:linear-gradient(180deg,#4fc3f7,#0288d1) !important; color:#04121c !important;',
                '  border:none !important; border-radius:9px !important; font-weight:800 !important;',
                '  letter-spacing:1.4px !important; padding:11px 26px !important; animation:none !important; }',
                '& .vtool-btn{ border-radius:8px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(56,189,248,0.16) !important;',
                '  border-color:var(--st-a) !important; color:var(--st-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
