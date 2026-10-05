/* ============================================================================
 * EXPERIENCE 02 — COMMAND
 * Paradigm: SEARCH-FIRST. You type what you want instead of hunting for it.
 *
 * The problem it attacks: the app has ~500 buttons and 51 tools spread across a
 * header, a toolbar, five tool menus, a settings dropdown, two rails and a zone
 * inspector. Everything is *somewhere*, and knowing where is the whole learning
 * curve. Command inverts that — one bar, type three letters, hit Enter.
 *
 * Crucially it does NOT remove the toolbar: it moves it into a drawer with an
 * always-visible trigger, so every tool is one click away exactly as before and
 * ALSO reachable by name. Two routes to the same real buttons.
 *
 * The palette drives the app by calling .click() on the REAL control nodes
 * returned by SPBX.indexControls(), so every action behaves identically to the
 * owner clicking it himself — no reimplementation, no divergence.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '02-command',
        name: 'Command',
        tagline: 'Type what you want. 500 controls, one search bar.',
        paradigm: 'Search-first command palette',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
            /* 1. Width back to the artwork (see engine dockPopout notes). */

            // Search-first means the rails need not be permanently open: they
            // collapse to 26px labelled spines and expand on hover or focus.
            // This is what makes Command look like nothing else in the set —
            // at rest the canvas owns almost the entire window.


            ctx.addClass(document.body, 'xp-cmd-spines');

            // A permanent label on each spine: collapsed must never read as
            // removed, so each rail still says what it is when it is narrow.
            [['#leftPanel', 'ZONES'], ['#rightPanel', 'FINISHES / LAYERS / ZONE']].forEach(function (pair) {
                var rail = ctx.q(pair[0]);
                if (rail) ctx.mk('div', { cls: 'xp-cmd-spinelabel', text: pair[1], into: rail, first: true });
            });

            /* 2. Channel squares into the free height below the artwork. */
            var container = ctx.q('#splitViewContainer');
            var strip = ctx.q('#previewTopStrip');
            if (container && strip) {
                ctx.move(strip, container);
                ctx.addClass(strip, 'xp-cmd-strip');
            }

            /* ---------------------------------------------------------------
             * 3. THE TOOLBAR BECOMES A DRAWER
             * Not hidden — parked behind a permanent trigger. The tool buttons
             * are the same nodes with the same handlers; they just live in a
             * panel that slides down instead of a bar that is always eating
             * 46px whether or not you are using a tool.
             * ------------------------------------------------------------ */
            var toolbar = ctx.q('#spbTopToolbar');
            var drawer = null;
            if (toolbar) {
                drawer = ctx.mk('div', {
                    cls: 'xp-cmd-drawer spbx-scroll-y',
                    attrs: { 'aria-label': 'All tools' },
                    into: 'body'
                });
                ctx.move(toolbar, drawer);
            }

            /* ---------------------------------------------------------------
             * 4. THE COMMAND BAR — the hero of this experience
             * ------------------------------------------------------------ */
            var bar = ctx.mk('div', { cls: 'xp-cmd-bar', into: '#centerPanel', first: true });
            var trigger = ctx.mk('button', {
                cls: 'xp-cmd-trigger',
                attrs: { type: 'button', 'aria-label': 'Open command palette' },
                html: '<span class="xp-cmd-ico">⌕</span>' +
                      '<span class="xp-cmd-hint">Type a command…</span>' +
                      '<kbd>Ctrl</kbd><kbd>K</kbd>'
            });
            bar.appendChild(trigger);

            var toolsBtn = ctx.mk('button', {
                cls: 'xp-cmd-toolsbtn',
                attrs: { type: 'button', 'aria-expanded': 'false', 'aria-label': 'Show all tools' },
                html: '⚙ Tools'
            });
            bar.appendChild(toolsBtn);
            ctx.on(toolsBtn, 'click', function () {
                var open = document.body.classList.toggle('xp-cmd-drawer-open');
                toolsBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
                ctx.refit();
            });
            ctx.onTeardown(function () { document.body.classList.remove('xp-cmd-drawer-open'); });

            // RENDER rides in the command bar — the one action that must never
            // be a search result you have to go find.
            var renderBtn = ctx.q('#btnRender');
            if (renderBtn) { ctx.move(renderBtn, bar); ctx.addClass(renderBtn, 'xp-cmd-render'); }

            // The rest of the action bar floats out of the vertical flow.
            var bottomBar = ctx.q('#previewBottomBar');
            if (bottomBar) {
                // Into the channel strip so it SHARES a row instead of forming
                // its own band. In flow at full width it wrapped to 285px tall
                // and cut the squares to 171sq.
                var _strip = ctx.q('#previewTopStrip');
                if (_strip) ctx.move(bottomBar, _strip);
                ctx.addClass(bottomBar, 'spbx-relocated');
                ctx.addClass(bottomBar, 'xp-cmd-dock');
            }
            var opts = ctx.q('#toolOptionsBar');
            if (opts) {
                ctx.addClass(opts, 'xp-cmd-hud');
            }

            /* ---------------------------------------------------------------
             * 5. THE PALETTE
             * ------------------------------------------------------------ */
            var sheet = ctx.mk('div', { cls: 'spbx-sheet xp-cmd-sheet', into: 'body' });
            var inner = ctx.mk('div', { cls: 'spbx-sheet-inner' });
            sheet.appendChild(inner);
            var input = ctx.mk('input', {
                cls: 'xp-cmd-input',
                attrs: { type: 'text', placeholder: 'Search tools, finishes, settings…',
                         'aria-label': 'Command search', autocomplete: 'off', spellcheck: 'false' }
            });
            var list = ctx.mk('div', { cls: 'xp-cmd-list spbx-scroll-y', attrs: { role: 'listbox' } });
            inner.appendChild(input);
            inner.appendChild(list);

            var index = [], results = [], cursor = 0;

            function refreshIndex() {
                // Re-scraped on every open: the app builds controls lazily
                // (zone inspector, finish rows), so a boot-time snapshot would
                // go stale the moment a zone is selected.
                index = SPBX.indexControls().filter(function (c) {
                    return c.el !== trigger && c.el !== toolsBtn && !sheet.contains(c.el);
                });
            }

            function score(item, q) {
                var hay = (item.label + ' ' + item.group + ' ' + item.hint).toLowerCase();
                var i = hay.indexOf(q);
                if (i === -1) {
                    // subsequence match so "brsh" still finds "Brush Tool"
                    var k = 0;
                    for (var j = 0; j < hay.length && k < q.length; j++) if (hay[j] === q[k]) k++;
                    return k === q.length ? 1 : 0;
                }
                var lab = item.label.toLowerCase();
                if (lab === q) return 100;
                if (lab.indexOf(q) === 0) return 60;
                if (i === 0) return 40;
                return 20 - Math.min(19, i / 8);
            }

            function render() {
                var q = input.value.trim().toLowerCase();
                results = (!q ? index.slice(0, 60)
                              : index.map(function (it) { return { it: it, s: score(it, q) }; })
                                     .filter(function (r) { return r.s > 0; })
                                     .sort(function (a, b) { return b.s - a.s; })
                                     .slice(0, 60)
                                     .map(function (r) { return r.it; }));
                cursor = 0;
                list.innerHTML = '';
                if (!results.length) {
                    var none = document.createElement('div');
                    none.className = 'xp-cmd-none';
                    none.textContent = 'Nothing matches “' + input.value + '”';
                    list.appendChild(none);
                    return;
                }
                results.forEach(function (it, i) {
                    var row = document.createElement('div');
                    row.className = 'xp-cmd-row' + (i === 0 ? ' sel' : '');
                    row.setAttribute('role', 'option');
                    var g = document.createElement('span');
                    g.className = 'xp-cmd-group';
                    g.textContent = it.group;
                    var l = document.createElement('span');
                    l.className = 'xp-cmd-label';
                    l.textContent = it.label;
                    row.appendChild(l);
                    row.appendChild(g);
                    row.addEventListener('mouseenter', function () { select(i); });
                    row.addEventListener('click', function () { run(i); });
                    list.appendChild(row);
                });
            }

            function select(i) {
                var rows = list.querySelectorAll('.xp-cmd-row');
                if (!rows.length) return;
                cursor = Math.max(0, Math.min(rows.length - 1, i));
                rows.forEach(function (r, n) { r.classList.toggle('sel', n === cursor); });
                var el = rows[cursor];
                if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
            }

            function run(i) {
                var it = results[i == null ? cursor : i];
                if (!it || !it.el) return;
                close();
                // Click the REAL node — identical to the owner clicking it.
                try {
                    if (it.el.disabled) return;
                    it.el.scrollIntoView({ block: 'nearest' });
                    it.el.click();
                } catch (e) { /* a control that refuses is the app's call, not ours */ }
            }

            function open() {
                refreshIndex();
                sheet.classList.add('open');
                input.value = '';
                render();
                setTimeout(function () { input.focus(); }, 10);
            }
            function close() { sheet.classList.remove('open'); }

            ctx.on(trigger, 'click', open);
            ctx.on(input, 'input', render);
            ctx.on(sheet, 'click', function (e) { if (e.target === sheet) close(); });
            ctx.on(input, 'keydown', function (e) {
                if (e.key === 'ArrowDown') { e.preventDefault(); select(cursor + 1); }
                else if (e.key === 'ArrowUp') { e.preventDefault(); select(cursor - 1); }
                else if (e.key === 'Enter') { e.preventDefault(); run(); }
                else if (e.key === 'Escape') { e.preventDefault(); close(); }
            });
            ctx.on(document, 'keydown', function (e) {
                if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                    e.preventDefault();
                    if (sheet.classList.contains('open')) close(); else open();
                }
            }, true);

            /* ---------------------------------------------------------------
             * 6. VISUAL LANGUAGE — near-zero chrome, keyboard-forward
             * ------------------------------------------------------------ */
            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:10px; --xp-accent:#7c8cff; }',
                '& #splitViewContainer{ padding:6px !important; gap:6px; }',

                /* Header thins right down; the command bar is the new focus. */
                '& .header{ background:#0a0b10 !important; border-bottom:1px solid var(--xp-line) !important; }',

                /* Command bar */
                '& .xp-cmd-bar{',
                '  display:flex; align-items:center; gap:8px;',
                '  padding:7px 12px; flex:0 0 auto;',
                '  background:#0a0b10; border-bottom:1px solid var(--xp-line);',
                '}',
                '& .xp-cmd-trigger{',
                '  flex:1 1 auto; display:flex; align-items:center; gap:8px;',
                '  height:34px; padding:0 12px; cursor:text;',
                '  background:#131622; border:1px solid rgba(124,140,255,0.28);',
                '  border-radius:9px; color:var(--xp-dim); font-size:12.5px;',
                '  text-align:left; transition:border-color .15s, background .15s;',
                '}',
                '& .xp-cmd-trigger:hover{ border-color:var(--xp-accent); background:#161a29; }',
                '& .xp-cmd-ico{ font-size:14px; color:var(--xp-accent); }',
                '& .xp-cmd-hint{ flex:1 1 auto; }',
                '& .xp-cmd-bar kbd{',
                '  font:600 10px/1 ui-monospace,Menlo,Consolas,monospace; color:var(--xp-dim);',
                '  background:#1c2133; border:1px solid rgba(255,255,255,0.12);',
                '  border-radius:4px; padding:3px 5px;',
                '}',
                '& .xp-cmd-toolsbtn{',
                '  height:34px; padding:0 14px; cursor:pointer; font-size:12px; font-weight:600;',
                '  background:#131622; color:var(--xp-ink);',
                '  border:1px solid var(--xp-line); border-radius:9px;',
                '}',
                '& .xp-cmd-toolsbtn:hover{ border-color:var(--xp-accent); color:#fff; }',
                '& .xp-cmd-render{',
                '  height:34px !important; padding:0 22px !important;',
                '  background:linear-gradient(180deg,#8b9aff,#5b6ae0) !important;',
                '  color:#08091a !important; border:none !important; border-radius:9px !important;',
                '  font-weight:800 !important; letter-spacing:0.5px !important;',
                '  animation:none !important; box-shadow:0 4px 16px rgba(124,140,255,0.32) !important;',
                '}',

                /* Tools drawer */
                '& .xp-cmd-drawer{',
                '  position:fixed; left:0; right:0; top:62px; z-index:9100;',
                '  max-height:0; overflow:hidden;',
                '  background:rgba(10,11,16,0.98); border-bottom:1px solid var(--xp-line);',
                '  box-shadow:0 18px 40px rgba(0,0,0,0.6);',
                '  transition:max-height .2s ease;',
                '}',
                '&.xp-cmd-drawer-open .xp-cmd-drawer{ max-height:46vh; overflow-y:auto; }',
                '& .xp-cmd-drawer #spbTopToolbar{ position:static !important; }',

                /* Palette */
                '& .xp-cmd-sheet .spbx-sheet-inner{ background:#0e1018; }',
                '& .xp-cmd-input{',
                '  width:100%; box-sizing:border-box; height:56px; padding:0 20px;',
                '  background:transparent; border:none; border-bottom:1px solid var(--xp-line);',
                '  color:var(--xp-ink); font-size:17px; outline:none;',
                '}',
                '& .xp-cmd-list{ max-height:min(52vh,460px); padding:6px; }',
                '& .xp-cmd-row{',
                '  display:flex; align-items:center; gap:10px; justify-content:space-between;',
                '  padding:9px 14px; border-radius:8px; cursor:pointer; color:var(--xp-ink); font-size:13px;',
                '}',
                '& .xp-cmd-row.sel{ background:rgba(124,140,255,0.16); box-shadow:inset 0 0 0 1px rgba(124,140,255,0.4); }',
                '& .xp-cmd-label{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }',
                '& .xp-cmd-group{ flex:0 0 auto; font-size:10px; color:var(--xp-dim); letter-spacing:0.4px; text-transform:uppercase; }',
                '& .xp-cmd-none{ padding:22px; text-align:center; color:var(--xp-dim); font-size:13px; }',

                /* Floating bands + channel strip */
                '& .xp-cmd-dock{ padding:6px 10px !important; gap:8px !important; height:auto !important;',
                '  min-height:0 !important; max-height:none !important; flex:0 0 auto !important; }',
                '& .xp-cmd-hud{ padding:3px 10px !important; height:auto !important; }',
                '& .xp-cmd-strip{ flex:0 0 auto !important; padding:4px 8px !important;',
                '  min-height:0 !important; background:transparent !important; border:none !important; }',
                '& .xp-cmd-strip #specChannelDock{ background:transparent !important; border:none !important; padding:0 !important; }',

                '& .left-panel, & .right-panel{ background:#0b0d13 !important;',
                '  border-color:var(--xp-line) !important; position:relative !important;',
                '  transition:width .18s ease, min-width .18s ease, max-width .18s ease !important; }',
                '&.xp-cmd-spines .left-panel > *:not(.xp-cmd-spinelabel),',
                '&.xp-cmd-spines .right-panel > *:not(.xp-cmd-spinelabel){',
                '  opacity:0; pointer-events:none; transition:opacity .14s ease; }',
                '&.xp-cmd-spines .left-panel:hover, &.xp-cmd-spines .left-panel:focus-within{',
                '  width:230px !important; min-width:230px !important; max-width:230px !important;',
                '  z-index:140 !important; }',
                '&.xp-cmd-spines .right-panel:hover, &.xp-cmd-spines .right-panel:focus-within{',
                '  width:292px !important; min-width:292px !important; max-width:292px !important;',
                '  z-index:140 !important; }',
                '&.xp-cmd-spines .left-panel:hover > *, &.xp-cmd-spines .left-panel:focus-within > *,',
                '&.xp-cmd-spines .right-panel:hover > *, &.xp-cmd-spines .right-panel:focus-within > *{',
                '  opacity:1; pointer-events:auto; }',
                '&.xp-cmd-spines .left-panel:hover .xp-cmd-spinelabel,',
                '&.xp-cmd-spines .right-panel:hover .xp-cmd-spinelabel{ display:none; }',
                '& .xp-cmd-spinelabel{ position:absolute; top:12px; left:0; right:0; margin:0 auto;',
                '  text-align:center; writing-mode:vertical-rl; transform:rotate(180deg);',
                '  font:700 8.5px/1 ui-monospace,Menlo,Consolas,monospace; letter-spacing:2.2px;',
                '  color:#6b7a94; pointer-events:none; z-index:2; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
