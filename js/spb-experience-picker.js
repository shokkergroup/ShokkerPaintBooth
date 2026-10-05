/* ============================================================================
 * SPB EXPERIENCE PICKER — 2026-07-29 (Claude)
 * The owner-facing way to try the 20 experiences in the real app.
 *
 *   Ctrl+Shift+X   open / close the gallery
 *   [  and  ]      step to the previous / next experience without opening it
 *   Esc            close
 *
 * Deliberately keyboard-first and self-contained: it does not touch the app's
 * settings markup, so it cannot break anything that ships. Choosing "Classic"
 * restores today's app exactly (the engine's teardown puts every moved node
 * back where it came from).
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX || window.SPBXPicker) return;

    var open = false, root = null, listEl = null;

    function build() {
        root = document.createElement('div');
        root.id = 'spbxPicker';
        root.setAttribute('role', 'dialog');
        root.setAttribute('aria-label', 'Experience gallery');
        root.innerHTML =
            '<div class="spbxp-inner">' +
              '<div class="spbxp-head">' +
                '<div>' +
                  '<div class="spbxp-title">EXPERIENCE GALLERY</div>' +
                  '<div class="spbxp-sub">Same app, same tools, nothing removed — 20 ways to use it. ' +
                  '<kbd>[</kbd> <kbd>]</kbd> to step, <kbd>Esc</kbd> to close.</div>' +
                '</div>' +
                '<button class="spbxp-x" type="button" aria-label="Close">×</button>' +
              '</div>' +
              '<div class="spbxp-list"></div>' +
            '</div>';
        document.body.appendChild(root);
        listEl = root.querySelector('.spbxp-list');
        root.querySelector('.spbxp-x').addEventListener('click', close);
        root.addEventListener('click', function (e) { if (e.target === root) close(); });

        var css = document.createElement('style');
        css.setAttribute('data-spbx', 'picker');
        css.textContent = [
            '#spbxPicker{position:fixed;inset:0;z-index:99999;display:none;',
            '  align-items:flex-start;justify-content:center;',
            '  background:rgba(3,5,10,.82);backdrop-filter:blur(10px);',
            '  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;}',
            '#spbxPicker.on{display:flex;}',
            '#spbxPicker .spbxp-inner{margin-top:6vh;width:min(980px,94vw);max-height:86vh;',
            '  display:flex;flex-direction:column;background:#0e1219;color:#e8eef7;',
            '  border:1px solid rgba(255,255,255,.12);border-radius:16px;overflow:hidden;',
            '  box-shadow:0 40px 110px rgba(0,0,0,.75);}',
            '#spbxPicker .spbxp-head{display:flex;align-items:flex-start;justify-content:space-between;',
            '  gap:16px;padding:18px 22px;border-bottom:1px solid rgba(255,255,255,.10);}',
            '#spbxPicker .spbxp-title{font-size:14px;font-weight:800;letter-spacing:2.4px;}',
            '#spbxPicker .spbxp-sub{margin-top:5px;font-size:11.5px;color:#93a3b8;}',
            '#spbxPicker kbd{background:#1c2333;border:1px solid rgba(255,255,255,.16);',
            '  border-radius:4px;padding:1px 5px;font:600 10px/1 ui-monospace,Menlo,monospace;}',
            '#spbxPicker .spbxp-x{background:transparent;border:none;color:#93a3b8;',
            '  font-size:26px;line-height:1;cursor:pointer;padding:0 4px;}',
            '#spbxPicker .spbxp-x:hover{color:#fff;}',
            '#spbxPicker .spbxp-list{overflow-y:auto;padding:14px;display:grid;',
            '  grid-template-columns:repeat(auto-fill,minmax(212px,1fr));gap:10px;}',
            '#spbxPicker .spbxp-card{text-align:left;cursor:pointer;padding:12px 13px;',
            '  background:#141a24;border:1px solid rgba(255,255,255,.10);border-radius:11px;',
            '  color:inherit;display:flex;flex-direction:column;gap:5px;transition:.14s;}',
            '#spbxPicker .spbxp-card:hover{border-color:#7c8cff;transform:translateY(-2px);}',
            '#spbxPicker .spbxp-card.on{border-color:#7c8cff;',
            '  box-shadow:0 0 0 2px rgba(124,140,255,.32);background:#18203a;}',
            '#spbxPicker .spbxp-n{font:700 9px/1 ui-monospace,Menlo,monospace;color:#6b7a94;letter-spacing:1.4px;}',
            '#spbxPicker .spbxp-name{font-size:14px;font-weight:750;}',
            '#spbxPicker .spbxp-para{font-size:10px;letter-spacing:.7px;text-transform:uppercase;color:#7c8cff;}',
            '#spbxPicker .spbxp-tag{font-size:11px;color:#93a3b8;line-height:1.4;}'
        ].join('');
        document.head.appendChild(css);
    }

    function render() {
        if (!listEl) return;
        var cur = SPBX.current || 'classic';
        var rows = [{ id: 'classic', name: 'Classic', paradigm: 'Today’s app',
                      tagline: 'Exactly what ships now. Nothing moved.' }].concat(SPBX.list());
        listEl.innerHTML = '';
        rows.forEach(function (p, i) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'spbxp-card' + (p.id === cur ? ' on' : '');
            b.innerHTML =
                '<span class="spbxp-n">' + (i === 0 ? '00' : String(i).padStart(2, '0')) + '</span>' +
                '<span class="spbxp-name"></span>' +
                '<span class="spbxp-para"></span>' +
                '<span class="spbxp-tag"></span>';
            b.querySelector('.spbxp-name').textContent = p.name || p.id;
            b.querySelector('.spbxp-para').textContent = p.paradigm || '';
            b.querySelector('.spbxp-tag').textContent = p.tagline || '';
            b.addEventListener('click', function () { SPBX.apply(p.id); render(); });
            listEl.appendChild(b);
        });
    }

    function show() {
        if (!root) build();
        render();
        root.classList.add('on');
        open = true;
        // 2026-08-05: packs are lazy now (they were 37% of the app's JS on every
        // boot). The gallery is the one place that needs them ALL, so fetch on
        // open and re-render as they register. First open pays; the boot no
        // longer does.
        if (SPBX.ensureAllPacks && SPBX.MANIFEST && SPBX.packs.length < SPBX.MANIFEST.length
            && !show._loading) {
            show._loading = true;
            SPBX.ensureAllPacks().then(function () { show._loading = false; render(); });
        }
    }
    function close() { if (root) root.classList.remove('on'); open = false; }

    document.addEventListener('keydown', function (e) {
        return;   // [SPB-DECLUTTER2 2026-08-29] Experiences parked (owner) - hotkeys (Ctrl+Shift+X, step-through) disabled; delete this line to restore.
        if (e.ctrlKey && e.shiftKey && (e.key === 'X' || e.key === 'x')) {
            e.preventDefault();
            if (open) close(); else show();
            return;
        }
        if (e.key === 'Escape' && open) { e.preventDefault(); close(); return; }
        // Step through without opening — the fastest way to compare.
        var typing = e.target && /input|textarea|select/i.test(e.target.tagName);
        if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key === '[') { e.preventDefault(); SPBX.cycle(-1); if (open) render(); }
        if (e.key === ']') { e.preventDefault(); SPBX.cycle(1); if (open) render(); }
    }, true);

    window.SPBXPicker = { show: show, close: close };

    // A permanent, discoverable way in — a chip in the header, next to the
    // other command buttons, so this is not a hidden keyboard secret.
    function mountChip() {
        var host = document.querySelector('.header') || document.body;
        if (document.getElementById('spbxPickerChip')) return;
        var b = document.createElement('button');
        b.id = 'spbxPickerChip';
        b.type = 'button';
        b.className = 'header-command-btn';
        b.title = 'Experience Gallery — 20 ways to use the same app (Ctrl+Shift+X)';
        b.setAttribute('aria-label', 'Open experience gallery');
        b.textContent = '◈ EXPERIENCES';
        b.style.cssText = 'cursor:pointer;';
        b.addEventListener('click', show);
        host.appendChild(b);
    }
    /* mountChip disabled on BOTH boot paths [SPB-HEADER-SLIM 2026-08-29]: Experiences moved to
       the Settings menu (window.SPBXPicker.show()); Ctrl+Shift+X still works. The chip builder
       stays in source for re-add. */
    void mountChip;
})();
