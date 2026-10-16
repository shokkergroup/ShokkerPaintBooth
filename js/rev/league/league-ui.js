/* league-ui.js - [SPB-REV-LEAGUE 2026-10-10] the League Pack panel (js/rev/league/league-core.js does the work).
 * Entry point: Car > League Pack...   One livery, a roster of drivers: numbers, names, team colours and sponsors per driver, a preview grid,
 * then Render All into <folder>/<customer id>/ with the same file names a normal RENDER writes.
 * Docked like the other tool panels (POLISH-H shell classes, POLISH-I dock); nothing in the page layout moves when it opens.
 * Kill switch: window.SPB_REV_LEAGUE_OFF (see core).
 */
(function (root) {
    'use strict';
    if (root.SpbRevLeagueUI) return;
    var doc = root.document, TAG = '[SPB-REV-LEAGUE]';
    function core() { return root.SpbRevLeague; }
    function off() { return !core() || core().off(); }
    function warn(w, e) { try { console.warn(TAG, w, e && e.message || e); } catch (_) {} }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k); } catch (_) {} }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function $(sel, el) { return (el || panel || doc).querySelector(sel); }
    function $$(sel, el) { return Array.prototype.slice.call((el || panel || doc).querySelectorAll(sel)); }

    var ICON = {
        grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
        x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
        check: '<path d="M20 6 9 17l-5-5"/>',
        alert: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
        plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
        upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
        folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    };
    function svg(k, sz) { return '<svg class="spb-lg-svg" viewBox="0 0 24 24" width="' + (sz || 14) + '" height="' + (sz || 14) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }

    var panel = null, tab = 'roster', sel = null, moved = false, view = 'paint', shield = null, layoutHooked = false, pvTimer = 0, bigBusy = false, msgPaste = '';
    var CLEAR_ARM = 0;

    // ------------------------------------------------------------------ build
    function chips(group, items) {
        return '<div class="spb-lg-chips" role="group">' + items.map(function (i) { return '<button type="button" class="spb-lg-chip" data-chip="' + group + '.' + i[0] + '" aria-pressed="false">' + i[1] + '</button>'; }).join('') + '</div>';
    }
    function row(label, inner, cls) { return '<div class="spb-lg-row' + (cls ? ' ' + cls : '') + '"><label>' + label + '</label>' + inner + '</div>'; }
    function colour(k, t) { return '<input type="color" data-o="' + k + '" title="' + t + '" aria-label="' + t + '">'; }
    function numIn(k, lo, hi, st, t, w) { return '<input type="number" data-o="' + k + '" min="' + lo + '" max="' + hi + '" step="' + st + '" title="' + t + '" aria-label="' + t + '" style="width:' + (w || 52) + 'px">'; }
    function build() {
        if (panel && panel.isConnected) return panel;
        var fonts = []; try { fonts = root.SpbRevNumbers.fonts(); } catch (e) { fonts = ['Impact', 'Arial Black']; }
        var fontOpts = '<option value="">From Number Kit</option>' + fonts.map(function (f) { return '<option value="' + esc(f) + '">' + esc(f) + '</option>'; }).join('');
        panel = doc.createElement('div'); panel.id = 'spbLeaguePack'; panel.className = 'spb-ph-panel spb-lg-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'League Pack'); panel.style.display = 'none';
        panel.innerHTML =
            '<div class="spb-ph-head" data-drag="1"><span class="spb-ph-ttl">' + svg('grid', 16) + '<span>League Pack</span></span><button type="button" class="spb-ph-x" data-act="close" title="Close (Esc)" aria-label="Close">' + svg('x', 14) + '</button></div>' +
            '<div class="spb-lg-tabs" role="tablist" aria-label="League Pack steps">' +
                '<button type="button" role="tab" data-tab="roster" aria-pressed="true">1  Roster</button><button type="button" role="tab" data-tab="look" aria-pressed="false">2  Look</button><button type="button" role="tab" data-tab="grid" aria-pressed="false">3  Preview &amp; Render</button></div>' +
            '<div class="spb-lg-body">' +
              // ---- roster
              '<section class="spb-lg-pane" data-pane="roster">' +
                '<div class="spb-lg-bar"><button type="button" data-act="import" title="Read a .csv / .tsv / .txt roster file">' + svg('upload') + 'Import File…</button><button type="button" data-act="paste" aria-pressed="false" title="Paste rows from a spreadsheet">Paste Rows</button>' +
                  '<button type="button" data-act="addrow" title="Add one empty driver row">' + svg('plus') + 'Add Row</button><span class="spb-lg-gap"></span><button type="button" data-act="clear" title="Remove every driver">Clear Roster</button>' +
                  '<input type="file" data-file="roster" accept=".csv,.tsv,.txt,text/csv,text/plain" hidden></div>' +
                '<div class="spb-lg-pastebox" hidden><textarea data-paste spellcheck="false" aria-label="Pasted roster rows" placeholder="Driver Name, Customer ID, Number, Team Colour, Sponsor Logo, Name Text&#10;Alex Rivera, 482913, 48, red, bigco, ARIVERA&#10;(a header row is optional; commas, tabs or semicolons all work)"></textarea>' +
                  '<div class="spb-lg-pastebtns"><span class="spb-lg-pmsg" aria-live="polite"></span><span class="spb-lg-gap"></span><button type="button" data-act="paste-add">Add To Roster</button><button type="button" data-act="paste-use" class="spb-lg-prime">Use These Rows</button></div></div>' +
                '<div class="spb-lg-tablewrap"><table class="spb-lg-table" aria-label="Driver roster"><thead><tr><th class="c-n">#</th><th class="c-name">Driver</th><th class="c-id">Customer ID</th><th class="c-no">No.</th><th class="c-team">Team Colour</th><th class="c-sp">Sponsor</th><th class="c-tx">Name Text</th><th class="c-st"></th></tr></thead><tbody data-rows></tbody></table></div>' +
                '<div class="spb-lg-sum" data-sum aria-live="polite"></div><div class="spb-lg-issues" data-issues></div>' +
                '<p class="spb-lg-hint">Customer IDs name the folders and the car_num_ / car_spec_ files. Team colours are names (red, navy) or #hex; up to three separated by / (main, accent, trim).</p>' +
              '</section>' +
              // ---- look
              '<section class="spb-lg-pane" data-pane="look" hidden>' +
                '<div class="spb-lg-sec">Numbers</div>' +
                row('Places', chips('places', [['left', 'Left Door'], ['right', 'Right Door'], ['roof', 'Roof']])) +
                row('Font', '<select data-o="font" aria-label="Number font" title="Font for the numbers (the Number Kit\'s own font when left as is)">' + fontOpts + '</select>') +
                row('Colours', '<span class="spb-lg-sub">Fill</span>' + colour('fill', 'Number colour') + '<span class="spb-lg-sub">Outline</span>' + colour('ring', 'Number outline colour') + '<label class="spb-lg-chk"><input type="checkbox" data-o="shadow">Shadow</label>' + '<span class="spb-lg-sub">Size</span>' + numIn('size', 40, 160, 1, 'Number size, % of the car\'s own number', 54) + '<span class="spb-lg-unit">%</span>') +
                row('Small Ones', '<label class="spb-lg-chk" title="Also replaces the small numbers on the fenders, bumper or nose with the driver\'s number, each in its own size and direction"><input type="checkbox" data-o="allNumbers">Replace Every Number On The Car (Including Small Ones)</label>') +
                '<p class="spb-lg-hint" data-numnote></p>' +
                '<div class="spb-lg-sec">Team Colour</div>' +
                row('Recolour', '<label class="spb-lg-chk"><input type="checkbox" data-o="teamOn">Use The Team Colour Column</label>') +
                '<p class="spb-lg-hint">The livery\'s main colour becomes the first team colour (Colourway Studio does the recolour, so shading and decals stay). Drivers with an empty team colour keep the original livery.</p>' +
                '<div class="spb-lg-sec">Name Text</div>' +
                row('Names', '<label class="spb-lg-chk"><input type="checkbox" data-o="nameOn">Add A Name To Every Driver</label>') +
                row('Where', '<select data-o="nameSlot" aria-label="Where the name goes"><option value="rails">Roof Rails</option><option value="quarters">Rear Quarters</option><option value="tv">TV Panels</option><option value="hood">Hood</option><option value="deck">Trunk</option></select>' +
                    '<select data-o="nameFrom" aria-label="Which text"><option value="auto">Name Text Column, Else Driver</option><option value="name">Driver Name Always</option></select>') +
                row('Text', '<span class="spb-lg-sub">Fill</span>' + colour('nameFill', 'Name colour') + '<span class="spb-lg-sub">Outline</span>' + colour('nameLine', 'Name outline colour') + '<label class="spb-lg-chk"><input type="checkbox" data-o="nameCaps">Capitals</label>' + '<span class="spb-lg-sub">Size</span>' + numIn('nameSize', 30, 200, 1, 'Name size, %', 54) + '<span class="spb-lg-unit">%</span>') +
                '<p class="spb-lg-hint" data-winnote>Names go on the part you pick, sized to its space.</p>' +
                '<div class="spb-lg-sec">Sponsor Logos</div>' +
                row('Logos', '<button type="button" data-act="logos">' + svg('plus') + 'Add Logo Files…</button><input type="file" data-file="logos" accept="image/*" multiple hidden><label class="spb-lg-chk"><input type="checkbox" data-o="logoOn">Place Them</label>') +
                '<div class="spb-lg-logos" data-logos></div>' +
                row('On', chips('logoSlots', [['hood', 'Hood'], ['quarters', 'Rear Quarters'], ['tv', 'TV Panels'], ['deck', 'Trunk'], ['doors', 'Doors']])) +
                row('Size', numIn('logoSize', 30, 200, 1, 'Logo size, %', 54) + '<span class="spb-lg-unit">%</span><span class="spb-lg-hint" style="margin:0 0 0 8px">Match a row\'s Sponsor cell to a file name.</span>') +
              '</section>' +
              // ---- grid + render
              '<section class="spb-lg-pane" data-pane="grid" hidden>' +
                row('Pack Folder', '<input type="text" data-folder spellcheck="false" placeholder="D:\\League\\Round 5" aria-label="Pack folder" title="Each driver renders into a sub-folder of this folder, named by customer ID"><button type="button" data-act="choose" title="Choose a folder">' + svg('folder') + 'Choose…</button>', 'spb-lg-folder') +
                '<p class="spb-lg-hint" data-foldernote></p>' +
                '<div class="spb-lg-big" data-big hidden></div>' +
                '<div class="spb-lg-grid" data-grid role="list" aria-label="Driver previews"></div>' +
              '</section>' +
            '</div>' +
            '<div class="spb-lg-status" data-status aria-live="polite"><div class="spb-lg-line" data-line></div><div class="spb-lg-prog" data-prog hidden><i></i></div></div>' +
            '<div class="spb-ph-foot"><button type="button" data-act="apply" disabled title="Put the selected driver on the project itself (each step gets its own Undo)">Apply This Driver To The Project</button><span class="spb-lg-gap"></span>' +
                '<button type="button" data-act="close">Close</button><button type="button" data-act="cancel" hidden title="Stops after the driver being rendered has finished; Resume Render carries on">Cancel</button><button type="button" data-act="preview" class="spb-ph-primary">Preview All</button><button type="button" data-act="render" class="spb-lg-render">Render All</button></div>';
        doc.body.appendChild(panel);
        wire();
        return panel;
    }

    // ------------------------------------------------------------------ wiring
    function wire() {
        panel.addEventListener('click', onClick);
        panel.addEventListener('change', onChange);
        panel.addEventListener('keydown', function (e) { if (e.key === 'Enter' && e.target.matches && e.target.matches('.spb-lg-table input')) { e.target.blur(); } e.stopPropagation(); }, false);
        panel.addEventListener('pointerdown', onDragStart);
        panel.addEventListener('dblclick', function (e) { if (e.target.closest && e.target.closest('.spb-ph-head') && !e.target.closest('button')) { moved = false; dock(); } });
        panel.addEventListener('paste', function (e) { e.stopPropagation(); });
        panel.addEventListener('input', function (e) { if (e.target.matches && e.target.matches('[data-folder]')) { core().state.folder = e.target.value; folderNote(); core().saveLocal(); core().emit('opts'); } });
        var rf = $('[data-file="roster"]'), lf = $('[data-file="logos"]');
        rf.addEventListener('change', function () { var f = rf.files && rf.files[0]; if (!f) return; var r = new FileReader(); r.onload = function () { loadText(String(r.result || ''), f.name, true); rf.value = ''; }; r.readAsText(f); });
        lf.addEventListener('change', function () { var fs = lf.files; if (!fs || !fs.length) return; core().addLogoFiles(fs).then(function (res) { var bad = res.filter(function (x) { return !x.ok; }); if (bad.length) toast('Not added: ' + bad.map(function (b) { return b.name + ' (' + b.why + ')'; }).join('; '), 'warn'); fillLogos(); renderRoster(); }); lf.value = ''; });
        core().on(onCore);
        doc.addEventListener('keydown', function (e) {
            if (!isOpen()) return;
            if (core().state.busy && (e.ctrlKey || e.metaKey) && !(panel.contains(e.target))) { e.stopPropagation(); e.preventDefault(); return; }
            if (e.key === 'Escape' && !core().state.busy && !(e.target.closest && e.target.closest('.spb-ph-panel') && !panel.contains(e.target))) { e.stopPropagation(); close(); }
        }, true);
        root.addEventListener('resize', function () { if (isOpen() && !moved) dock(); });
    }
    var drag = null;
    function onDragStart(e) {
        var h = e.target.closest && e.target.closest('.spb-ph-head'); if (!h || (e.target.closest && e.target.closest('button'))) return;
        var r = panel.getBoundingClientRect(); drag = { dx: e.clientX - r.left, dy: e.clientY - r.top };
        var mv = function (ev) { if (!drag) return; panel.style.left = Math.max(0, Math.min((root.innerWidth || 1200) - 120, ev.clientX - drag.dx)) + 'px'; panel.style.top = Math.max(0, Math.min((root.innerHeight || 800) - 60, ev.clientY - drag.dy)) + 'px'; moved = true; };
        var up = function () { doc.removeEventListener('pointermove', mv); doc.removeEventListener('pointerup', up); drag = null; };
        doc.addEventListener('pointermove', mv); doc.addEventListener('pointerup', up);
    }
    function dock() {
        if (!panel) return;
        var H = root.__spbPolishH;
        if (H && typeof H.applyDock === 'function' && !(H.isOff && H.isOff())) { try { H.applyDock(panel); return; } catch (e) { warn('dock', e); } }
        var vw = root.innerWidth || 1200, vh = root.innerHeight || 800, w = panel.offsetWidth || 620;       // POLISH-H absent: a corner of our own
        panel.style.left = Math.max(4, Math.min(vw - w - 4, 8)) + 'px'; panel.style.top = '120px'; panel.style.maxHeight = Math.max(260, vh - 128) + 'px';
    }
    function hookLayout() {
        if (layoutHooked) return; layoutHooked = true;
        try { if (root.__spbPolishH && root.__spbPolishH.onLayout) root.__spbPolishH.onLayout(function () { if (isOpen() && !moved) dock(); }); } catch (e) { warn('onLayout', e); }
    }

    // ------------------------------------------------------------------ open / close
    function isOpen() { return !!(panel && panel.style.display !== 'none'); }
    function open(opts) {
        if (off()) return Promise.resolve(false);
        build(); hookLayout();
        panel.style.display = ''; panel.classList.add('spb-ph-front'); if (!moved) dock();
        var st = core().state; $('[data-folder]').value = st.folder || '';
        syncOpts(); fillLogos(); renderRoster(); renderGrid(); folderNote(); setTab((opts && opts.tab) || tab); refreshButtons(); line('');
        return Promise.resolve(true);
    }
    function close() {
        if (!panel || core().state.busy) return;
        panel.style.display = 'none'; sel = null;
    }
    function setTab(t) {
        tab = t;
        $$('.spb-lg-tabs button').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-tab') === t ? 'true' : 'false'); });
        $$('.spb-lg-pane').forEach(function (p) { p.hidden = p.getAttribute('data-pane') !== t; });
        if (t === 'grid') renderGrid();
        if (t === 'look') numNote();
        if (!moved) dock();
    }

    // ------------------------------------------------------------------ roster pane
    function rows() { return core().state.rows; }
    function cell(i, f, v, ph, cls, extra) { return '<td class="' + (cls || '') + '"><input type="text" data-r="' + i + '" data-f="' + f + '" value="' + esc(v) + '" spellcheck="false" autocomplete="off"' + (ph ? ' placeholder="' + ph + '"' : '') + (extra || '') + ' aria-label="' + f + ' row ' + (i + 1) + '"></td>'; }
    function renderRoster() {
        if (!panel) return;
        var tb = $('[data-rows]'), rs = rows();
        core().validate(rs, core().state.logos);
        tb.innerHTML = rs.length ? rs.map(function (r, i) {
            return '<tr data-row="' + i + '"><td class="c-n">' + (i + 1) + '</td>' + cell(i, 'name', r.name, 'Driver', 'c-name') + cell(i, 'custid', r.custid, '123456', 'c-id', ' inputmode="numeric" maxlength="7"') + cell(i, 'number', r.number, '48', 'c-no', ' inputmode="numeric" maxlength="3"') +
                '<td class="c-team"><span class="spb-lg-swr"></span><input type="text" data-r="' + i + '" data-f="team" value="' + esc(r.team) + '" spellcheck="false" autocomplete="off" placeholder="red" aria-label="team row ' + (i + 1) + '"></td>' +
                cell(i, 'sponsor', r.sponsor, 'logo', 'c-sp', ' list="spbLgLogoList"') + cell(i, 'text', r.text, '', 'c-tx') +
                '<td class="c-st"><span class="spb-lg-ok"></span><button type="button" class="spb-lg-del" data-del="' + i + '" title="Remove this driver" aria-label="Remove row ' + (i + 1) + '">' + svg('x', 12) + '</button></td></tr>';
        }).join('') : '<tr><td colspan="8" class="spb-lg-empty">No drivers yet. Import a CSV, paste rows from a spreadsheet, or add rows by hand.</td></tr>';
        rs.forEach(function (r, i) { paintRow(i); });
        summary(); refreshButtons();
    }
    function paintRow(i) {
        var tr = $('tr[data-row="' + i + '"]'); if (!tr) return; var r = rows()[i]; if (!r) return;
        tr.classList.toggle('bad', !r.ok); tr.classList.toggle('sel', sel === r.custid && !!r.custid);
        var st = $('.spb-lg-ok', tr), msg = r.errs.concat(r.warns).join(' ');
        st.innerHTML = r.errs.length ? svg('alert', 13) : (r.warns.length ? svg('alert', 13) : svg('check', 13));
        st.className = 'spb-lg-ok ' + (r.errs.length ? 'err' : r.warns.length ? 'warn' : 'good'); st.title = msg || 'Ready';
        $$('input[data-f]', tr).forEach(function (inp) {
            var f = inp.getAttribute('data-f'), bad = false;
            if (f === 'custid') bad = r.errs.some(function (m) { return /ID/.test(m); });
            if (f === 'number') bad = r.errs.some(function (m) { return /Number/.test(m); });
            if (f === 'team') bad = r.errs.some(function (m) { return /colour/.test(m); });
            if (f === 'sponsor') bad = r.warns.some(function (m) { return /Sponsor/.test(m); });
            inp.classList.toggle('bad', bad); inp.title = bad ? msg : '';
        });
        var sw = $('.spb-lg-swr', tr); sw.innerHTML = (r.hex || []).map(function (h) { return '<i style="background:' + h + '"></i>'; }).join('');
    }
    function summary() {
        var rs = rows(), errs = 0, warns = 0, bad = [];
        rs.forEach(function (r, i) { errs += r.errs.length; warns += r.warns.length; r.errs.forEach(function (m) { bad.push({ i: i, r: r, m: m, e: true }); }); r.warns.forEach(function (m) { bad.push({ i: i, r: r, m: m, e: false }); }); });
        var okN = rs.filter(function (r) { return r.ok; }).length;
        $('[data-sum]').textContent = rs.length ? rs.length + ' drivers, ' + okN + ' ready' + (errs ? ', ' + errs + ' to fix' : '') + (warns ? ', ' + warns + ' note' + (warns > 1 ? 's' : '') : '') : '';
        bad.sort(function (a, b) { return (b.e ? 1 : 0) - (a.e ? 1 : 0) || a.i - b.i; });
        $('[data-issues]').innerHTML = bad.slice(0, 5).map(function (b) { return '<div class="' + (b.e ? 'err' : 'warn') + '">Row ' + (b.i + 1) + (b.r.name ? ' (' + esc(b.r.name) + ')' : '') + ': ' + esc(b.m) + '</div>'; }).join('') + (bad.length > 5 ? '<div class="warn">And ' + (bad.length - 5) + ' more.</div>' : '');
    }
    var rowTimers = {};
    function onRowChange(inp) {
        var i = +inp.getAttribute('data-r'), f = inp.getAttribute('data-f'), r = rows()[i]; if (!r) return;
        var old = r.custid; r[f] = inp.value.trim(); if (f === 'number') r.number = r.number.replace(/^#/, '');
        core().validate(rows(), core().state.logos);
        rows().forEach(function (_, k) { paintRow(k); }); summary(); refreshButtons();
        core().saveLocal(); core().emit('rosteredit');
        // a fixed row refreshes its own tile (only when the grid already has previews)
        if (core().state.lastPreview && r.ok) { clearTimeout(rowTimers[i]); rowTimers[i] = setTimeout(function () { if (!core().state.busy) core().previewAll([r]).catch(function (e) { warn('row preview', e); }); else core().state.dirty = true; }, 700); }
        if (old !== r.custid && sel === old) sel = null;
        renderGrid();
    }
    function loadText(text, name, replace) {
        var p = core().parseRoster(text);
        if (!p.rows.length) { msgPaste = 'No rows found.'; var m0 = $('.spb-lg-pmsg'); if (m0) m0.textContent = msgPaste; toast('No rows found in ' + (name || 'that text') + '.', 'warn'); return false; }
        var next = replace ? p.rows : rows().map(function (r) { return { name: r.name, custid: r.custid, number: r.number, team: r.team, sponsor: r.sponsor, text: r.text }; }).concat(p.rows);
        core().setRoster(next); renderRoster(); renderGrid();
        var msg = 'Read ' + p.rows.length + ' driver' + (p.rows.length === 1 ? '' : 's') + (p.header ? ' (header row found)' : ' (no header row, columns read in the usual order)') + '.';
        var m = $('.spb-lg-pmsg'); if (m) m.textContent = msg; line(msg);
        return true;
    }

    // ------------------------------------------------------------------ look pane
    function syncOpts() {
        var o = core().state.opts, nk = core().numKit();
        $$('[data-chip]').forEach(function (b) { var p = b.getAttribute('data-chip').split('.'); b.setAttribute('aria-pressed', o[p[0]] && o[p[0]][p[1]] ? 'true' : 'false'); });
        $$('[data-o]').forEach(function (inp) {
            var k = inp.getAttribute('data-o'), v = o[k];
            if (k === 'fill') v = nk.fill; if (k === 'ring') v = (nk.ring1 && nk.ring1.color) || o.ring; if (k === 'shadow') v = nk.shadow ? nk.shadow.on : o.shadow;
            if (k === 'font') v = o.font || '';
            if (inp.type === 'checkbox') inp.checked = !!v; else if (v != null) inp.value = v;
        });
        numNote();
    }
    function numNote() {
        var n = $('[data-numnote]'); if (!n) return; var o = core().state.opts;
        var tail = o.allNumbers !== false ? ' Small numbers elsewhere (fender, bumper, nose) are replaced too, each in its own size and direction.' : ' Small numbers elsewhere on the car (a fender number) stay as the template has them.';
        n.textContent = (o.styleSet ? 'Numbers replace the car\'s own numbers in the same place, size and slant, in the style set here.' : 'Numbers replace the car\'s own numbers in the same place, size and slant, in your last Number Kit style. Change a value here to set a style for the pack.') + tail;
        var wn = $('[data-winnote]');
        if (wn) { var hasWs = false; try { hasWs = (root.SpbProCar.parts() || []).some(function (p) { return /windshield|windscreen/i.test(p); }); } catch (e) {} wn.textContent = hasWs ? 'Names go on the part you pick, sized to its space.' : 'Names go on the part you pick, sized to its space (this car\'s map has no windshield part, so a windshield banner is not offered).'; }
    }
    function fillLogos() {
        var L = core().state.logos, keys = Object.keys(L), box = $('[data-logos]');
        box.innerHTML = keys.length ? keys.map(function (k) { return '<span class="spb-lg-logo" title="' + esc(L[k].name) + ' (' + L[k].w + ' x ' + L[k].h + ')"><img alt="" src="' + L[k].canvas.toDataURL('image/png') + '"><b>' + esc(k) + '</b><button type="button" data-rmlogo="' + esc(k) + '" aria-label="Remove ' + esc(k) + '">' + svg('x', 10) + '</button></span>'; }).join('') : '<span class="spb-lg-hint">No logos yet. File names (without the extension) are what the roster\'s Sponsor column matches.</span>';
        var dl = doc.getElementById('spbLgLogoList'); if (!dl) { dl = doc.createElement('datalist'); dl.id = 'spbLgLogoList'; panel.appendChild(dl); }
        dl.innerHTML = keys.map(function (k) { return '<option value="' + esc(k) + '">'; }).join('');
    }
    function onOpt(inp) {
        var o = core().state.opts, k = inp.getAttribute('data-o'), v = inp.type === 'checkbox' ? inp.checked : (inp.type === 'number' ? +inp.value : inp.value);
        if (inp.type === 'number' && !isFinite(v)) return;
        if (k === 'fill' || k === 'ring' || k === 'shadow' || k === 'font') {
            if (!o.styleSet) { var nk = core().numKit(); o.fill = nk.fill; o.ring = (nk.ring1 && nk.ring1.color) || o.ring; o.shadow = nk.shadow ? !!nk.shadow.on : o.shadow; o.styleSet = true; }      // first touch: freeze what the Number Kit style was, then change one thing
            o[k] = v;
        } else o[k] = v;
        core().saveLocal(); core().emit('opts'); markStale(); numNote();
    }
    function onChip(b) {
        var p = b.getAttribute('data-chip').split('.'), o = core().state.opts; o[p[0]] = o[p[0]] || {};
        o[p[0]][p[1]] = !o[p[0]][p[1]]; b.setAttribute('aria-pressed', o[p[0]][p[1]] ? 'true' : 'false');
        core().saveLocal(); core().emit('opts'); markStale();
    }

    // ------------------------------------------------------------------ grid pane
    function stale(d) { var r = core().state.results[d.custid]; if (!r || !r.thumb) return false; try { return !!core().state.tmpl && core().driverHash(d, core().state.tmpl) !== r.thumbHash; } catch (e) { return false; } }
    function markStale() { if (panel && tab === 'grid') renderGrid(); refreshButtons(); }
    function tileHtml(d, i) {
        var r = core().state.results[d.custid] || {}, st = r.state || (r.thumb ? 'ready' : 'none');
        var label = { working: 'Working…', done: r.seconds ? 'Rendered, ' + r.seconds + ' s' : 'Rendered', skipped: 'Already Rendered', error: 'Error', pending: 'Waiting', ready: 'Preview Ready', none: d.ok ? 'No Preview Yet' : 'Fix The Roster' }[st] || '';
        if (st === 'ready' && stale(d)) label = 'Out Of Date';
        var cls = 'spb-lg-tile ' + st + (sel === d.custid ? ' sel' : '') + (!d.ok ? ' bad' : '') + (stale(d) ? ' stale' : '');
        return '<button type="button" role="listitem" class="' + cls + '" data-tile="' + esc(d.custid) + '" ' + (d.ok ? '' : 'disabled ') + 'title="' + esc((d.name || 'Driver') + ' #' + d.number + (r.error ? ': ' + r.error : '')) + '"><span class="spb-lg-img">' + (r.thumb ? '<img alt="" src="' + r.thumb + '">' : '<em>' + esc('#' + (d.number || '?')) + '</em>') + '</span>' +
            '<span class="spb-lg-tn"><b>#' + esc(d.number) + '</b> ' + esc(d.name || d.custid) + '</span><span class="spb-lg-ts">' + esc(label) + '</span></button>';
    }
    function renderGrid() {
        if (!panel) return; var g = $('[data-grid]'); if (!g) return;
        var rs = rows();
        g.innerHTML = rs.length ? rs.map(tileHtml).join('') : '<p class="spb-lg-hint">Add drivers on the Roster step first.</p>';
    }
    function updateTile(d) {
        if (!panel) return; var old = $('[data-tile="' + (window.CSS && CSS.escape ? CSS.escape(d.custid) : d.custid) + '"]'); if (!old) { renderGrid(); return; }
        var tmp = doc.createElement('div'); tmp.innerHTML = tileHtml(d, 0); old.replaceWith(tmp.firstChild);
    }
    function folderNote() {
        var n = $('[data-foldernote]'); if (!n) return; var f = core().state.folder || '', t = '';
        if (core().isIracingPath(f)) t = 'That is inside iRacing\'s paint folder. A league pack is for sharing, so pick a folder of your own; iRacing only reads files directly inside a car\'s folder.';
        else if (f && !/^[a-zA-Z]:[\\\/]|^\\\\/.test(f)) t = 'Use a full path, like D:\\League\\Round 5.';
        else t = 'Each driver renders into a sub-folder named by customer ID, plus a contact sheet and a README. Drivers already rendered with the same look are skipped (resume).';
        n.textContent = t; n.classList.toggle('warn', core().isIracingPath(f) || (!!f && !/^[a-zA-Z]:[\\\/]|^\\\\/.test(f)));
    }
    async function openBig(id) {
        var d = rows().filter(function (r) { return r.custid === id; })[0]; if (!d || !d.ok || core().state.busy) return;
        sel = id; renderGrid(); refreshButtons();
        var big = $('[data-big]'); big.hidden = false; big.innerHTML = '<div class="spb-lg-bighead"><b>#' + esc(d.number) + '</b> ' + esc(d.name) + '<span class="spb-lg-gap"></span><span class="spb-lg-seg"><button type="button" data-view="paint" aria-pressed="true">Paint</button><button type="button" data-view="spec" aria-pressed="false">Spec</button></span><button type="button" data-act="closebig" aria-label="Close preview" title="Close preview">' + svg('x', 12) + '</button></div><div class="spb-lg-bigimg"><span class="spb-lg-wait">Rendering the preview…</span></div>';
        view = 'paint'; bigBusy = true;
        try {
            var h = core().driverHash(d, core().state.tmpl || core().templateHash()), r0 = core().state.results[d.custid];
            if (!(r0 && r0.big && r0.bigHash === h)) { await core().previewOne(d); r0 = core().state.results[d.custid]; r0.bigHash = h; }
            showBig(d);
        } catch (e) { var w = $('.spb-lg-wait'); if (w) w.textContent = 'The preview failed: ' + (e && e.message || e); }
        bigBusy = false;
    }
    function showBig(d) {
        var big = $('[data-big]'); if (!big || big.hidden) return; var r = core().state.results[d.custid] || {};
        var im = $('.spb-lg-bigimg', big); var src = view === 'spec' ? (r.bigSpec || '') : (r.big || '');
        im.innerHTML = src ? '<img alt="' + esc(d.name) + ' ' + view + ' preview" src="' + src + '">' : '<span class="spb-lg-wait">No ' + view + ' preview.</span>';
        $$('[data-view]', big).forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-view') === view ? 'true' : 'false'); });
        if (r.notes && r.notes.length) im.insertAdjacentHTML('beforeend', '<div class="spb-lg-notes">' + r.notes.map(esc).join(' ') + '</div>');
    }

    // ------------------------------------------------------------------ status, buttons, core events
    function line(t, kind) { if (!panel) return; var l = $('[data-line]'); l.textContent = t || ''; l.className = 'spb-lg-line' + (kind ? ' ' + kind : ''); }
    function prog(a, b) { var p = $('[data-prog]'); if (!p) return; if (a == null) { p.hidden = true; return; } p.hidden = false; $('i', p).style.width = Math.round(100 * a / Math.max(1, b)) + '%'; }
    function refreshButtons() {
        if (!panel) return; var st = core().state, busy = !!st.busy, ok = rows().filter(function (r) { return r.ok; }).length;
        $('[data-act="preview"]').disabled = busy || !ok; $('[data-act="render"]').disabled = busy || !ok || !(st.folder || '').trim();
        $('[data-act="cancel"]').hidden = !busy; $('[data-act="close"]:not(.spb-ph-x)').hidden = busy; $('[data-act="apply"]').disabled = busy || !sel;
        $('[data-act="render"]').textContent = st.lastRun && (st.lastRun.cancelled || st.lastRun.failed) ? 'Resume Render' : 'Render All';
        $('[data-act="render"]').title = (st.folder || '').trim() ? 'Render every ready driver into the pack folder at 2048 x 2048 (drivers already done are skipped)' : 'Choose a pack folder first';
        $$('.spb-lg-tabs button, .spb-lg-bar button').forEach(function (b) { b.disabled = busy && b.closest('.spb-lg-bar'); });
        panel.classList.toggle('busy', busy);
    }
    function shieldOn(on) {
        if (on && !shield) { shield = doc.createElement('div'); shield.id = 'spbLgShield'; shield.setAttribute('aria-hidden', 'true'); doc.body.appendChild(shield); }
        if (shield) shield.style.display = on ? '' : 'none';
    }
    var total = 0, doneN = 0;
    function onCore(ev, data) {
        if (!panel) return;
        if (ev === 'roster') { renderRoster(); renderGrid(); fillLogos(); }
        else if (ev === 'busy') { shieldOn(true); total = rows().filter(function (r) { return r.ok; }).length; doneN = 0; refreshButtons(); prog(0, total); line(data.kind === 'render' ? 'Rendering…' : data.kind === 'one' ? 'Rendering the preview…' : 'Building previews…'); }
        else if (ev === 'tile') {
            updateTile(data.d);
            if (data.state === 'done' || data.state === 'skipped' || data.state === 'ready' || data.state === 'error') { doneN++; prog(doneN, total); }
            if (data.state === 'working') line((data.index != null ? 'Driver ' + (data.index + 1) + ' of ' + data.total + ': ' : '') + (data.d.name || data.d.custid) + ' (#' + data.d.number + ')…');
            if (data.state === 'done') { var secs = core().state.results[data.d.custid].seconds; line('Rendered ' + (data.d.name || data.d.custid) + ' in ' + secs + ' s.'); }
        }
        else if (ev === 'idle') {
            shieldOn(false); prog(null); refreshButtons(); renderGrid();
            var rep = data && (data.check || (data.summary && data.summary.check));
            if (data && data.kind === 'render' && data.summary) {
                var s = data.summary;
                var t = s.cancelled ? 'Cancelled after ' + (s.done + s.skipped) + ' of ' + s.total + ' drivers. Press Resume Render to carry on; finished drivers are skipped.' :
                    'Done: ' + s.done + ' rendered' + (s.skipped ? ', ' + s.skipped + ' already done' : '') + (s.failed ? ', ' + s.failed + ' failed' : '') + ' in ' + s.wall + ' s' + (s.avg ? ' (' + s.avg + ' s per driver)' : '') + '. Contact sheet and README are in the pack folder.';
                line(t, s.failed ? 'warn' : ''); if (s.failures && s.failures.length) toast('Some drivers failed: ' + s.failures.slice(0, 2).join('; '), 'warn');
            } else if (data && data.kind === 'preview') { var lp = core().state.lastPreview; line('Previews ready: ' + (lp ? lp.n : 0) + ' drivers in ' + (lp ? lp.sec : 0) + ' s.'); }
            else if (data && data.kind === 'one') line('');
            if (rep && rep.unchanged === false) toast('League Pack: the project differs from before the run. Use Undo if that was not intended.', 'warn');
            if (core().state.dirty && !core().state.busy) { core().state.dirty = false; core().previewAll().catch(function () {}); }
        }
        else if (ev === 'error') { shieldOn(false); prog(null); line(data && data.error || 'Something went wrong.', 'err'); refreshButtons(); }
        else if (ev === 'cancel') line('Cancelling after this driver…');
        else if (ev === 'applied') { renderGrid(); refreshButtons(); }
    }

    // ------------------------------------------------------------------ clicks
    function onClick(e) {
        var t = e.target.closest && e.target.closest('button'); if (!t || t.disabled) return;
        var act = t.getAttribute('data-act');
        if (t.hasAttribute('data-tab')) return setTab(t.getAttribute('data-tab'));
        if (t.hasAttribute('data-chip')) return onChip(t);
        if (t.hasAttribute('data-del')) { var i = +t.getAttribute('data-del'); var rs = rows().slice(); rs.splice(i, 1); core().setRoster(rs); renderRoster(); renderGrid(); return; }
        if (t.hasAttribute('data-rmlogo')) { delete core().state.logos[t.getAttribute('data-rmlogo')]; core().validate(rows(), core().state.logos); fillLogos(); renderRoster(); return; }
        if (t.hasAttribute('data-tile')) return void openBig(t.getAttribute('data-tile'));
        if (t.hasAttribute('data-view')) { view = t.getAttribute('data-view'); var d = rows().filter(function (r) { return r.custid === sel; })[0]; if (d) showBig(d); return; }
        if (act === 'close') return close();
        if (act === 'closebig') { $('[data-big]').hidden = true; return; }
        if (act === 'import') return void $('[data-file="roster"]').click();
        if (act === 'logos') return void $('[data-file="logos"]').click();
        if (act === 'paste') { var pb = $('.spb-lg-pastebox'); pb.hidden = !pb.hidden; t.setAttribute('aria-pressed', pb.hidden ? 'false' : 'true'); if (!pb.hidden) $('[data-paste]').focus(); return; }
        if (act === 'paste-use') { if (loadText($('[data-paste]').value, 'the pasted rows', true)) { $('[data-paste]').value = ''; } return; }
        if (act === 'paste-add') { if (loadText($('[data-paste]').value, 'the pasted rows', false)) { $('[data-paste]').value = ''; } return; }
        if (act === 'addrow') { var rs2 = rows().map(function (r) { return { name: r.name, custid: r.custid, number: r.number, team: r.team, sponsor: r.sponsor, text: r.text }; }); rs2.push({ name: '', custid: '', number: '', team: '', sponsor: '', text: '' }); core().setRoster(rs2); renderRoster(); renderGrid(); var last = $$('tr[data-row] input[data-f="name"]').pop(); if (last) last.focus(); return; }
        if (act === 'clear') { if (!CLEAR_ARM || Date.now() - CLEAR_ARM > 3500) { CLEAR_ARM = Date.now(); t.textContent = 'Really Clear?'; setTimeout(function () { if (t.isConnected) { t.textContent = 'Clear Roster'; CLEAR_ARM = 0; } }, 3600); return; } CLEAR_ARM = 0; t.textContent = 'Clear Roster'; core().setRoster([]); core().state.results = {}; renderRoster(); renderGrid(); return; }
        if (act === 'choose') return void chooseFolder();
        if (act === 'preview') { setTab('grid'); core().previewAll(null, { force: false }).catch(function (e) { line(String(e && e.message || e), 'err'); }); return; }
        if (act === 'render') { setTab('grid'); core().renderAll({ title: 'League Pack' }).catch(function (e) { line(String(e && e.message || e), 'err'); }); return; }
        if (act === 'cancel') return void core().cancel();
        if (act === 'apply') { var dr = rows().filter(function (r) { return r.custid === sel; })[0]; if (dr) core().applyDriver(dr).then(function () { line('Applied ' + (dr.name || dr.custid) + ' to the project.'); }).catch(function (er) { toast(String(er && er.message || er), 'warn'); }); return; }
    }
    function onChange(e) {
        var t = e.target;
        if (t.matches && t.matches('[data-r]')) return onRowChange(t);
        if (t.matches && t.matches('[data-o]')) return onOpt(t);
    }
    function chooseFolder() {
        fetch('/api/native-dialog', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' }, body: JSON.stringify({ mode: 'folder', title: 'Choose the league pack folder', filter: '', startPath: core().state.folder || '' }) })
            .then(function (r) { return r.json(); }).then(function (j) {
                if (j && j.path && !j.cancelled) { var f = $('[data-folder]'); f.value = j.path; core().state.folder = j.path; folderNote(); core().saveLocal(); core().emit('opts'); refreshButtons(); }
                else if (j && j.success === false) toast('The folder chooser failed: ' + (j.error || 'unknown'), 'warn');
            }).catch(function (er) { toast('The folder chooser is not available here. Type the folder path instead.', 'warn'); });
    }

    // ------------------------------------------------------------------ menu entry (Car menu)
    function addMenuItem() {
        if (off()) return false;
        var pop = doc.querySelector('#spbSymMenu .spb-tb-pop'); if (!pop) return false;
        if (pop.querySelector('[data-league]')) return true;
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'vtool-btn'; b.setAttribute('data-league', 'open');
        b.title = 'League Pack: one livery for a whole grid of drivers (numbers, names, team colours, sponsors), previewed and rendered into one folder per driver';
        b.innerHTML = '<span class="spb-mi-ico spb-sym-ico">' + svg('grid') + '</span> League Pack…';
        var anchor = pop.querySelector('[data-sponsor]') || pop.querySelector('[data-nkit]');
        if (anchor && anchor.nextSibling) pop.insertBefore(b, anchor.nextSibling); else pop.appendChild(b);
        b.addEventListener('click', function (e) { e.preventDefault(); var m = pop.closest('details'); if (m) m.removeAttribute('open'); open(); });
        return true;
    }
    function boot(n) {
        if (off()) { if ((n || 0) < 120) setTimeout(function () { boot((n || 0) + 1); }, 1000); return; }
        var m = addMenuItem();
        if (!m && (n || 0) < 80) setTimeout(function () { boot((n || 0) + 1); }, 500);
        else if (m) setInterval(function () { if (!off()) addMenuItem(); }, 3000);
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { boot(0); }); else boot(0);

    root.SpbRevLeagueUI = { open: open, close: close, isOpen: isOpen, panel: function () { return panel; }, setTab: setTab, selected: function () { return sel; }, openBig: openBig, renderRoster: renderRoster, renderGrid: renderGrid, loadText: loadText, syncOpts: syncOpts, fillLogos: fillLogos };
})(typeof window !== 'undefined' ? window : globalThis);
