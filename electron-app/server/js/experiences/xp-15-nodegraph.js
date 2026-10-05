/* ============================================================================
 * EXPERIENCE 15 — NODE GRAPH
 * Paradigm: DATAFLOW. The recipe is a wired chain you can see and click.
 *
 * The app's biggest conceptual gap is that the PIPELINE is invisible: source →
 * zone → base → pattern → spec overlay → rendered TGA. New users cannot form a
 * mental model because nothing on screen shows the order things happen in.
 * Node Graph draws that chain as wired nodes above the artwork; each node
 * reports live state (how many zones, which base, is a pattern set) and clicking
 * one jumps to the real control that edits it.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '15-nodegraph',
        name: 'Node Graph',
        tagline: 'See the pipeline: source → zone → base → pattern → spec → TGA.',
        paradigm: 'Dataflow chain',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            // The pipeline reads top-to-bottom down its own rail, replacing
            // the zones sidebar position, so the graph IS the left edge of the
            // app rather than one more horizontal band above the artwork.

            ctx.addClass(document.body, 'xp-ng-vertical');

            var graph = ctx.mk('div', {
                cls: 'xp-ng spbx-scroll-y', attrs: { 'aria-label': 'Recipe pipeline' }
            });
            var mainC = ctx.q('.main-container');
            var centerC = ctx.q('#centerPanel');
            if (mainC && centerC) mainC.insertBefore(graph, centerC);

            var NODES = [
                { id: 'src', t: 'SOURCE', sub: 'the car file',
                  state: function () {
                      var i = document.getElementById('paintFile');
                      var v = i && i.value ? i.value.split(/[\\/]/).pop() : '';
                      return v ? v.slice(0, 18) : 'none';
                  },
                  go: function () { var b = document.getElementById('paintFile'); if (b) { b.focus(); b.scrollIntoView({ block: 'nearest' }); } } },
                { id: 'zone', t: 'ZONES', sub: 'which pixels',
                  state: function () { return document.querySelectorAll('#zoneList .zone-card').length + ' zone(s)'; },
                  go: function () { var z = document.querySelector('#zoneList .zone-card'); if (z) z.click(); } },
                { id: 'base', t: 'BASE', sub: 'the paint',
                  state: function () {
                      var s = document.querySelector('#zoneEditorFloat .swatch-trigger, #zoneEditorFloat [id^="baseSwatch"]');
                      var txt = s ? (s.textContent || '').replace(/\s+/g, ' ').trim() : '';
                      return txt ? txt.slice(0, 18) : 'not set';
                  },
                  go: function () { var s = document.querySelector('#zoneEditorFloat .swatch-trigger'); if (s) s.click(); } },
                { id: 'pat', t: 'PATTERN', sub: 'the graphic',
                  state: function () {
                      var h = document.querySelector('#patternActiveBadge');
                      return (h && h.offsetParent) ? 'active' : 'none';
                  },
                  go: function () {
                      var el = Array.prototype.slice.call(document.querySelectorAll('#zoneEditorFloat .section-header'))
                          .filter(function (n) { return /PATTERN/i.test(n.textContent || ''); })[0];
                      if (el) el.click();
                  } },
                { id: 'spec', t: 'SPEC', sub: 'metal / rough / coat',
                  state: function () { return document.querySelectorAll('.spec-channel-dock-cell').length + ' channels'; },
                  go: function () { var c = document.querySelector('.spec-channel-dock-cell'); if (c) c.click(); } },
                { id: 'out', t: 'TGA', sub: 'to iRacing',
                  state: function () {
                      var s = document.getElementById('serverStatus');
                      return s && s.classList.contains('offline') ? 'server offline' : 'ready';
                  },
                  go: function () { var b = document.getElementById('btnRender'); if (b) b.click(); } }
            ];

            var refs = NODES.map(function (n, i) {
                if (i) {
                    var wire = ctx.mk('div', { cls: 'xp-ng-wire' });
                    graph.appendChild(wire);
                }
                var node = ctx.mk('button', {
                    cls: 'xp-ng-node', attrs: { type: 'button', 'data-n': n.id, title: n.sub },
                    html: '<span class="xp-ng-t">' + n.t + '</span>' +
                          '<span class="xp-ng-s"></span>' +
                          '<span class="xp-ng-sub">' + n.sub + '</span>'
                });
                graph.appendChild(node);
                ctx.on(node, 'click', function () {
                    try { n.go(); } catch (_) {}
                    refs.forEach(function (r) { r.node.classList.remove('on'); });
                    node.classList.add('on');
                });
                return { node: node, val: node.querySelector('.xp-ng-s'), def: n };
            });

            function tick() {
                refs.forEach(function (r) {
                    var v;
                    try { v = String(r.def.state()); } catch (_) { v = '—'; }
                    if (r.val.textContent !== v) r.val.textContent = v;
                    var empty = /^(none|not set|0 |server offline)/.test(v);
                    r.node.classList.toggle('empty', empty);
                });
            }
            tick();
            var iv = setInterval(tick, 1100);
            ctx.onTeardown(function () { clearInterval(iv); });

            ctx.css([
                '&{ --xp-ch:50px; --xp-radius:10px; --ng-a:#c084fc; --ng-ok:#4ade80; --ng-off:#3f3a4d; }',
                '& #splitViewContainer{ padding:8px !important; gap:8px; }',
                '& .main-container, & #centerPanel{ background:#0c0a14 !important; }',
                '& .header, & #spbTopToolbar{ background:#110e1c !important;',
                '  border-bottom:1px solid #241e38 !important; }',
                '& .left-panel, & .right-panel{ background:#110e1c !important; border-color:#241e38 !important; }',

                '& .xp-ng{ flex:0 0 178px; width:178px; display:flex; flex-direction:column;',
                '  align-items:stretch; gap:0; padding:12px 10px; overflow-y:auto;',
                '  background:#0e0b18; border-right:1px solid #241e38; }',
                '& .xp-ng-node{ width:100% !important; }',
                '& .xp-ng-node{ flex:0 0 auto; display:flex; flex-direction:column; align-items:flex-start;',
                '  gap:1px; min-width:112px; padding:7px 12px; cursor:pointer; text-align:left;',
                '  background:#171327; border:1px solid #2f2747; border-radius:9px; }',
                '& .xp-ng-node:hover{ border-color:var(--ng-a); }',
                '& .xp-ng-node.on{ border-color:var(--ng-a);',
                '  box-shadow:0 0 0 2px rgba(192,132,252,0.25), 0 0 18px rgba(192,132,252,0.25); }',
                '& .xp-ng-t{ font:800 9.5px/1 ui-monospace,Menlo,Consolas,monospace;',
                '  letter-spacing:1.4px; color:#cbb6ff; }',
                '& .xp-ng-s{ font:700 12px/1.3 system-ui,sans-serif; color:var(--ng-ok);',
                '  max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }',
                '& .xp-ng-node.empty .xp-ng-s{ color:#6b6280; }',
                '& .xp-ng-sub{ font:400 8.5px/1 system-ui,sans-serif; color:#6b6280; letter-spacing:0.3px; }',
                /* the wire between nodes, with an arrowhead */
                /* vertical wire with a downward arrowhead */
                '& .xp-ng-wire{ flex:0 0 22px; width:2px; height:22px; margin:0 auto;',
                '  background:linear-gradient(180deg,#2f2747,var(--ng-a)); position:relative; }',
                '& .xp-ng-wire::after{ content:""; position:absolute; left:50%; bottom:-1px;',
                '  width:6px; height:6px; margin-left:-4px;',
                '  border-right:2px solid var(--ng-a); border-bottom:2px solid var(--ng-a);',
                '  transform:rotate(45deg); }',

                '& #splitSource, & #splitPreview{ background:#07050d !important;',
                '  border:1px solid #2f2747 !important; border-radius:10px !important;',
                '  box-shadow:0 14px 36px rgba(0,0,0,0.55) !important; }',
                '& .xp-ng-strip{ flex:0 0 auto !important; gap:10px !important;',
                '  padding:6px 12px !important; min-height:0 !important; background:#110e1c !important;',
                '  border:1px solid #241e38 !important; border-radius:10px !important; }',
                '& .xp-ng-strip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:9px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& .xp-ng-strip .spec-channel-dock-cell{ background:#07050d !important;',
                '  border:1px solid #2f2747 !important; border-radius:7px !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:linear-gradient(135deg,#c084fc,#7c3aed) !important;',
                '  color:#0c0a14 !important; border:none !important; border-radius:9px !important;',
                '  font-weight:800 !important; letter-spacing:1.6px !important; padding:11px 26px !important;',
                '  animation:none !important; box-shadow:0 5px 18px rgba(192,132,252,0.35) !important; }',
                '& .vtool-btn{ border-radius:8px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(192,132,252,0.16) !important;',
                '  border-color:var(--ng-a) !important; color:var(--ng-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
