/* ============================================================================
 * EXPERIENCE 11 — TERMINAL
 * Paradigm: COMMAND LINE. You drive the app by typing verbs; the GUI is output.
 *
 * Distinct from 02 Command: that is a fuzzy PICKER (find a button by name).
 * This is a LANGUAGE — verbs with arguments, a scrollback of what happened, and
 * history with the up-arrow. `zone 3` selects zone 3. `tool brush` picks the
 * brush. `render` renders. `find candy` lists matching controls. Every command
 * resolves to a real control and clicks it, so the terminal can never do
 * something the buttons cannot.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '11-terminal',
        name: 'Terminal',
        tagline: 'Type verbs, not clicks. Scrollback, history, real commands.',
        paradigm: 'Command line',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            var term = ctx.mk('div', { cls: 'xp-tm', into: '#rightPanel' });
            var log = ctx.mk('div', { cls: 'xp-tm-log spbx-scroll-y', attrs: { role: 'log' } });
            var row = ctx.mk('div', { cls: 'xp-tm-row' });
            var ps1 = ctx.mk('span', { cls: 'xp-tm-ps1', text: 'spb ❯' });
            var input = ctx.mk('input', {
                cls: 'xp-tm-in',
                attrs: { type: 'text', spellcheck: 'false', autocomplete: 'off',
                         'aria-label': 'Command line', placeholder: "type 'help'" }
            });
            row.appendChild(ps1); row.appendChild(input);
            term.appendChild(log); term.appendChild(row);

            var history = [], hi = -1;

            function say(text, cls) {
                var l = document.createElement('div');
                l.className = 'xp-tm-line' + (cls ? ' ' + cls : '');
                l.textContent = text;
                log.appendChild(l);
                log.scrollTop = log.scrollHeight;
                while (log.childNodes.length > 200) log.removeChild(log.firstChild);
            }

            function controls() { return SPBX.indexControls(); }

            function clickLabel(q, groupHint) {
                var list = controls().filter(function (c) {
                    return !term.contains(c.el) &&
                           (!groupHint || c.group === groupHint);
                });
                var ql = q.toLowerCase();
                var exact = list.filter(function (c) { return c.label.toLowerCase() === ql; });
                var starts = list.filter(function (c) { return c.label.toLowerCase().indexOf(ql) === 0; });
                var has = list.filter(function (c) { return (c.label + ' ' + c.hint).toLowerCase().indexOf(ql) !== -1; });
                var hit = exact[0] || starts[0] || has[0];
                if (!hit) return null;
                try { hit.el.scrollIntoView({ block: 'nearest' }); hit.el.click(); } catch (_) {}
                return hit;
            }

            var VERBS = {
                help: function () {
                    say('commands:', 'ok');
                    say('  zone <n|name>     select a zone');
                    say('  tool <name>       pick a tool  (brush, eraser, wand, lasso…)');
                    say('  render            render the spec maps');
                    say('  find <text>       list matching controls');
                    say('  click <text>      click the best matching control');
                    say('  zoom <in|out|fit|100>');
                    say('  zones | tools     list what exists');
                    say('  clear             clear this scrollback');
                },
                zone: function (a) {
                    if (!a) return say('usage: zone <number|name>', 'err');
                    var cards = Array.prototype.slice.call(document.querySelectorAll('#zoneList .zone-card'));
                    var t = /^\d+$/.test(a) ? cards[parseInt(a, 10) - 1]
                        : cards.filter(function (c) {
                              return (c.textContent || '').toLowerCase().indexOf(a.toLowerCase()) !== -1;
                          })[0];
                    if (!t) return say('no zone matching "' + a + '"', 'err');
                    try { t.click(); } catch (_) {}
                    say('selected zone ' + (cards.indexOf(t) + 1), 'ok');
                },
                zones: function () {
                    var cards = document.querySelectorAll('#zoneList .zone-card');
                    if (!cards.length) return say('no zones', 'err');
                    Array.prototype.forEach.call(cards, function (c, i) {
                        say('  ' + (i + 1) + '  ' + (c.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 48));
                    });
                },
                tool: function (a) {
                    if (!a) return say('usage: tool <name>', 'err');
                    var hit = clickLabel(a, 'Tools') ||
                              controls().filter(function (c) {
                                  return c.el.classList && c.el.classList.contains('vtool-btn') &&
                                         (c.label + ' ' + c.hint).toLowerCase().indexOf(a.toLowerCase()) !== -1;
                              })[0];
                    if (!hit) return say('no tool matching "' + a + '"', 'err');
                    if (hit.el && hit.el.click) { try { hit.el.click(); } catch (_) {} }
                    say('tool → ' + hit.label, 'ok');
                },
                tools: function () {
                    Array.prototype.slice.call(document.querySelectorAll('.vtool-btn'))
                        .slice(0, 60).forEach(function (b) {
                            say('  ' + (b.getAttribute('aria-label') || b.id || '?'));
                        });
                },
                render: function () {
                    var b = document.getElementById('btnRender');
                    if (!b) return say('render button not found', 'err');
                    b.click();
                    say('render started', 'ok');
                },
                zoom: function (a) {
                    if (typeof window.canvasZoom !== 'function') return say('zoom unavailable', 'err');
                    var k = (a || 'fit').toLowerCase();
                    window.canvasZoom(k === '100' ? '100' : k);
                    say('zoom → ' + k, 'ok');
                },
                find: function (a) {
                    if (!a) return say('usage: find <text>', 'err');
                    var hits = controls().filter(function (c) {
                        return !term.contains(c.el) &&
                               (c.label + ' ' + c.hint).toLowerCase().indexOf(a.toLowerCase()) !== -1;
                    }).slice(0, 20);
                    if (!hits.length) return say('nothing matches "' + a + '"', 'err');
                    hits.forEach(function (h) { say('  [' + h.group + '] ' + h.label); });
                    say(hits.length + ' shown — `click <text>` to run one', 'dim');
                },
                click: function (a) {
                    if (!a) return say('usage: click <text>', 'err');
                    var hit = clickLabel(a);
                    say(hit ? 'clicked → ' + hit.label : 'nothing matches "' + a + '"', hit ? 'ok' : 'err');
                },
                clear: function () { log.innerHTML = ''; }
            };

            function run(line) {
                var parts = line.trim().split(/\s+/);
                var verb = (parts.shift() || '').toLowerCase();
                var arg = parts.join(' ');
                say('spb ❯ ' + line, 'echo');
                if (!verb) return;
                if (VERBS[verb]) { try { VERBS[verb](arg); } catch (e) { say(String(e), 'err'); } }
                else {
                    // Unknown verb: treat the whole line as a control search, so
                    // the terminal degrades gracefully instead of scolding you.
                    var hit = clickLabel(line.trim());
                    say(hit ? 'clicked → ' + hit.label
                            : "unknown command '" + verb + "' — try `help`", hit ? 'ok' : 'err');
                }
            }

            ctx.on(input, 'keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    var v = input.value;
                    if (!v.trim()) return;
                    history.push(v); hi = history.length;
                    input.value = '';
                    run(v);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (hi > 0) { hi--; input.value = history[hi] || ''; }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (hi < history.length - 1) { hi++; input.value = history[hi] || ''; }
                    else { hi = history.length; input.value = ''; }
                }
            });
            ctx.on(document, 'keydown', function (e) {
                if (e.key === '`' && document.activeElement !== input) { e.preventDefault(); input.focus(); }
            });

            say('SHOKKER PAINT BOOTH — terminal experience', 'ok');
            say("type 'help' for commands, ` to focus, ↑ for history", 'dim');

            ctx.css([
                '&{ --xp-ch:48px; --xp-radius:0px; --tm-g:#7ee787; --tm-dim:#5a6b5c; --tm-err:#ff7b72; }',
                '& #splitViewContainer{ padding:6px !important; gap:6px; }',
                '& .main-container, & #centerPanel, & #canvasViewport{ background:#04060a !important; }',
                '& .header, & #spbTopToolbar{ background:#070b10 !important;',
                '  border-bottom:1px solid #16202b !important; }',
                '& .left-panel, & .right-panel{ background:#060a0e !important; border-color:#16202b !important; }',
                '& *{ border-radius:0 !important; }',
                '& .panel-header, & .rp-tab, & .zone-card, & .layer-row, & .vtool-label,',
                '& .section-header-label, & .split-pane-label, & .preview-dual-label, & .btn{',
                '  font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace !important;',
                '  letter-spacing:0.4px !important; }',

                '& .xp-tm{ flex:0 0 auto; display:flex; flex-direction:column;',
                '  height:132px; background:#020407; border-top:1px solid #16202b;',
                '  font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; }',
                '& .xp-tm-log{ flex:1 1 auto; padding:6px 10px; font-size:11.5px; line-height:1.55;',
                '  color:#9db3c0; min-height:0; }',
                '& .xp-tm-line.ok{ color:var(--tm-g); }',
                '& .xp-tm-line.err{ color:var(--tm-err); }',
                '& .xp-tm-line.dim{ color:var(--tm-dim); }',
                '& .xp-tm-line.echo{ color:#e6edf3; }',
                '& .xp-tm-row{ flex:0 0 auto; display:flex; align-items:center; gap:8px;',
                '  padding:6px 10px; border-top:1px solid #16202b; background:#04070c; }',
                '& .xp-tm-ps1{ color:var(--tm-g); font-size:12px; font-weight:700; }',
                '& .xp-tm-in{ flex:1 1 auto; background:transparent; border:none; outline:none;',
                '  color:#e6edf3; font-family:inherit; font-size:12.5px; caret-color:var(--tm-g); }',

                '& #splitSource, & #splitPreview{ background:#000 !important;',
                '  border:1px solid #16202b !important; }',
                '& #previewTopStrip{ flex:0 0 auto !important; padding:4px 8px !important;',
                '  min-height:0 !important; background:#060a0e !important;',
                '  border:1px solid #16202b !important; gap:8px !important; }',
                '& #previewTopStrip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:8px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:#0b2b14 !important; color:var(--tm-g) !important;',
                '  border:1px solid var(--tm-g) !important; font-weight:700 !important;',
                '  letter-spacing:2px !important; padding:10px 22px !important; animation:none !important; }',
                '& .vtool-btn{ animation:none !important; background:#080d12 !important;',
                '  border:1px solid #16202b !important; }',
                '& .vtool-btn.active{ background:#0b2b14 !important; color:var(--tm-g) !important;',
                '  border-color:var(--tm-g) !important; box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
