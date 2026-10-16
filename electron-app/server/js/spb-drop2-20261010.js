/* [SPB-DROP2 2026-10-10] lane DROP-2: the Shokk Drop page gets a product shell.
   Owner, 10:35: "people use it and like it but the interface is clunky ... build it BETTER".
   Audit (before): _easy_claude_work/drop2/AUDIT.md.
   - Clicking a card showed its preview off screen (y=1371).
   - Import & preview and SHOKK THE WORLD sat under the fold (y=1171 at 1920).
   - Commit was 614/921 px below the rail.
   - No card was visible at 1100.
   - "Use in Booth" opened a SECOND booth.
   - Each card had 9 actions in 10 px links.
   This file adds NO new import / delete / export logic. It re-homes the page's own controls and calls the page's own window functions.
   Every control the old page had stays in the DOM: same ids, same listeners, same endpoints, same files.
     1. LAYOUT: rail (drop tile, Type chips, folded sections, pinned action footer), gallery, and an INSPECTOR column showing the selected
        drop or the pending import (Commit sits right there). At 1100 the inspector is a drawer.
     2. CARDS: big thumb, name, and a hover bar (Use on car, More). The old action links are still on the card, hidden; the More menu and the
        inspector call those exact elements.
     3. DRAG: dragging files anywhere shows one overlay with targets: preview and import, SHOKK THE WORLD, batch import, add pack.
     4. KEYS: arrows move between cards, Enter opens, Space selects, Del deletes (asks), F favourite, U use on car, I import, / search,
        Esc closes, ? lists them.
     5. UPGRADES: Batch import (many images straight to the library, with a progress list). "Use on car" sends the drop to the Paint Booth
        that opened this page (window.opener, same origin), on the selected zone, a new whole-car zone or a named car part.
        That uses the booth's own assignFinishToSelected / SpbProZone.add. With no open booth it falls back to the old new-tab ?stagedMono=.
   Kill switch: ?drop2=off, localStorage SPB_DROP2_OFF=1 or window.SPB_DROP2_OFF = true -> the old page, untouched. */
(function () {
    'use strict';
    var doc = document, root = doc.documentElement;
    function off() {
        try { if (window.SPB_DROP2_OFF === true) return true; } catch (e) {}
        try { if (/[?&](drop2=off|SPB_DROP2_OFF=1)/i.test(location.search)) return true; } catch (e) {}
        try { if (localStorage.getItem('SPB_DROP2_OFF') === '1') return true; } catch (e) {}
        return false;
    }
    if (off()) { root.classList.remove('d2', 'd2-boot'); return; }
    if (window.__spbDrop2) return;
    window.__spbDrop2 = { version: '20261010d' };
    root.classList.add('d2');

    function $(id) { return doc.getElementById(id); }
    function el(tag, cls, html) { var e = doc.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
    function txt(e) { return (e && e.textContent || '').replace(/\s+/g, ' ').trim(); }
    function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
    function toast(m, k) { try { (window.showToast || function () {})(m, k || 'info'); } catch (e) {} }
    function typing(t) { var tag = t && t.tagName ? t.tagName.toUpperCase() : ''; return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || !!(t && t.isContentEditable); }
    function shown(e) { return !!e && getComputedStyle(e).display !== 'none'; }

    var app = doc.querySelector('.app'), aside = doc.querySelector('aside'), main = doc.querySelector('main'), header = doc.querySelector('header');
    if (!app || !aside || !main || !header) { root.classList.remove('d2', 'd2-boot'); return; }

    // ------------------------------------------------------------------ 1a. header: title + one-line purpose, "More" menu, back to the booth
    var tagline = header.querySelector('.tagline');
    if (tagline) { tagline.setAttribute('data-d2-old', tagline.innerHTML); tagline.textContent = 'Turn any image into a car finish with its own shine (spec). Share it as a .spbdrop.'; }
    var acts = header.querySelector('.header-actions');
    var backLink = acts ? acts.querySelector('a[href="/"]') : null;
    var moreBtn = el('button', 'btn d2-more-btn', 'More <span aria-hidden="true">▾</span>');
    moreBtn.type = 'button'; moreBtn.id = 'd2MoreBtn'; moreBtn.setAttribute('aria-haspopup', 'menu'); moreBtn.title = 'Guide, product bible, export the whole library, inbox folder, report a problem';
    var moreMenu = el('div', 'd2-more-menu'); moreMenu.id = 'd2MoreMenu'; moreMenu.setAttribute('role', 'menu'); moreMenu.hidden = true;
    if (acts) {
        Array.prototype.slice.call(acts.children).forEach(function (c) { if (c !== backLink) moreMenu.appendChild(c); });
        var inboxProxy = el('button', 'btn', 'Inbox folder import'); inboxProxy.type = 'button';
        inboxProxy.title = 'Batch-import every image in %APPDATA%\\ShokkerPaintBooth\\user_imports\\inbox (processed files move to inbox\\done)';
        inboxProxy.addEventListener('click', function () { if (typeof window.processUserImportInbox === 'function') window.processUserImportInbox(); });
        var keysBtn = el('button', 'btn', 'Keyboard shortcuts'); keysBtn.type = 'button'; keysBtn.addEventListener('click', showKeys);
        moreMenu.appendChild(inboxProxy); moreMenu.appendChild(keysBtn);
        acts.insertBefore(moreBtn, acts.firstChild);
        acts.appendChild(moreMenu);
        if (backLink) { acts.appendChild(backLink); backLink.textContent = '← Paint Booth'; }
        moreBtn.addEventListener('click', function (e) { e.stopPropagation(); toggleMore(); });
        moreMenu.addEventListener('click', function (e) { if (e.target.closest('button, a')) setTimeout(function () { toggleMore(false); }, 0); });
    }
    function toggleMore(force) {
        var open = force == null ? moreMenu.hidden : !!force;
        moreMenu.hidden = !open; moreBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) { var f = moreMenu.querySelector('button, a'); if (f) f.focus(); }
    }

    // ------------------------------------------------------------------ 1b. rail: drop tile, Type chips, folded sections, pinned footer
    var newCard = aside.querySelector('.card');            // the old "New drop" card: its rows are re-homed below, the card itself stays
    var libCard = aside.querySelectorAll('.card')[1];
    var kindSel = $('userImportKind');
    var railScroll = el('div', 'd2-rail-scroll'); railScroll.id = 'd2RailScroll';
    var railFoot = el('div', 'd2-rail-foot'); railFoot.id = 'd2RailFoot';
    var tile = el('button', 'd2-droptile',
        '<span class="d2-droptile-icon" aria-hidden="true">⤓</span>' +
        '<span class="d2-droptile-main">Drop art here, or click to choose</span>' +
        '<span class="d2-droptile-sub">PNG · JPG · WebP · drop several for a batch · Shift+drop = Shokk the World</span>');
    tile.type = 'button'; tile.id = 'd2DropTile'; tile.title = 'Choose an image to import and preview (I)';
    tile.addEventListener('click', function () { if (typeof window.openUserImportDialog === 'function') window.openUserImportDialog(true); });
    var oldHint = aside.querySelector(':scope > p.hint'); if (oldHint) oldHint.classList.add('d2-hide');

    // Type chips drive the real <select id="userImportKind"> (it stays in the DOM; every old listener keeps working)
    var KIND_SHORT = { paint_monolithic: 'Paint', pattern: 'Pattern', spec_overlay: 'Spec overlay', paint_spec_set: 'Paint + my spec', car_template: 'Whole car' };
    var typeSec = el('div', 'd2-sec d2-type');
    typeSec.appendChild(el('div', 'd2-sec-label', 'What are you importing?'));
    var chips = el('div', 'd2-chips'); chips.setAttribute('role', 'radiogroup'); chips.setAttribute('aria-label', 'Import type');
    if (kindSel) {
        Array.prototype.forEach.call(kindSel.options, function (o) {
            var c = el('button', 'd2-chip', esc(KIND_SHORT[o.value] || o.textContent)); c.type = 'button'; c.dataset.kind = o.value;
            c.setAttribute('role', 'radio'); c.title = o.textContent;
            c.addEventListener('click', function () { if (kindSel.value !== o.value) { kindSel.value = o.value; kindSel.dispatchEvent(new Event('change', { bubbles: true })); } syncChips(); });
            chips.appendChild(c);
        });
        kindSel.classList.add('d2-sr'); kindSel.tabIndex = -1;
        var kindLbl = aside.querySelector('label[for="userImportKind"]'); if (kindLbl) kindLbl.classList.add('d2-sr');
        kindSel.addEventListener('change', function () { syncChips(); setTimeout(syncSections, 0); });
    }
    typeSec.appendChild(chips);
    ['userImportKindHelp', 'userImportCarTemplateHint'].forEach(function (id) { var e = $(id); if (e) typeSec.appendChild(e); });
    function syncChips() {
        if (!kindSel) return;
        chips.querySelectorAll('.d2-chip').forEach(function (c) { var on = c.dataset.kind === kindSel.value; c.classList.toggle('on', on); c.setAttribute('aria-checked', on ? 'true' : 'false'); c.tabIndex = on ? 0 : -1; });
    }
    chips.addEventListener('keydown', function (e) {
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].indexOf(e.key) < 0) return;
        var list = Array.prototype.slice.call(chips.querySelectorAll('.d2-chip')), i = list.indexOf(doc.activeElement);
        if (i < 0) return; e.preventDefault();
        var n = list[(i + (e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 1) + list.length) % list.length]; n.focus(); n.click();
    });

    // folded sections; a section hides itself when every row in it is hidden by the page's own per-Type logic
    function section(id, title, rowIds, openByDefault) {
        var d = el('details', 'd2-sec d2-fold'); d.id = id;
        var s = el('summary', '', esc(title)); d.appendChild(s);
        var body = el('div', 'd2-fold-body'); d.appendChild(body);
        var rows = [];
        rowIds.forEach(function (rid) { var r = typeof rid === 'string' ? $(rid) : rid; if (r) { body.appendChild(r); rows.push(r); } });
        d._rows = rows; if (openByDefault) d.open = true;
        try { var k = localStorage.getItem('spbDrop2Fold:' + id); if (k === '1') d.open = true; else if (k === '0') d.open = false; } catch (e) {}
        d.addEventListener('toggle', function () { try { localStorage.setItem('spbDrop2Fold:' + id, d.open ? '1' : '0'); } catch (e) {} });
        return d;
    }
    var secDna = section('d2SecDna', 'Shine style (Import DNA)', ['userImportStyleRow', 'userImportVibeRow', 'userImportAlsoPatternRow'], false);
    var secChan = section('d2SecChan', 'Spec channel strength', ['userImportSpecChannelRow'], true);
    var secSet = section('d2SecSet', 'Use my own spec maps (optional)', ['userImportSetRow'], false);
    var secMix = section('d2SecMix', 'Remix + wildness', ['dnaRemixRow', 'shokkWildnessRow'], false);
    secMix.querySelector('summary').title = 'DNA Remix (style A + B) and spec wildness: used by Shokk the World';
    var secRec = section('d2SecRec', 'My DNA recipes', ['dnaPresetsRow'], false);
    var libRows = libCard ? Array.prototype.slice.call(libCard.children).filter(function (c) { return c.tagName !== 'H3'; }) : [];
    var cousin = aside.querySelector(':scope > p.hint:last-of-type'); if (cousin && cousin !== oldHint) libRows.push(cousin);
    var secLib = section('d2SecLib', 'Library list', libRows, false);
    if (libCard) libCard.classList.add('d2-hide');
    // the old "New drop" card keeps its <h3> + hidden bits; the visible rows now live in the sections
    var setRowH = $('userImportSetRow') && $('userImportSetRow').querySelector('h3'); if (setRowH) setRowH.classList.add('d2-hide');
    var SECTIONS = [secDna, secChan, secSet, secMix, secRec, secLib];
    function syncSections() {
        SECTIONS.forEach(function (d) { d.hidden = !d._rows.some(function (r) { return r.style.display !== 'none'; }); });
        if (kindSel && kindSel.value === 'paint_spec_set') secSet.open = true;   // the set IS the import for this Type
        var lib = $('userImportsStatus'); var s = secLib.querySelector('summary');
        if (s) s.textContent = 'Library list' + (lib && /^\d+/.test(txt(lib)) ? ' (' + txt(lib).match(/^\d+/)[0] + ')' : '');
        var w = $('shokkWildnessVal'), ms = secMix.querySelector('summary'); if (ms && w) ms.setAttribute('data-d2-val', txt(w));
    }
    var mo = new MutationObserver(function () { syncSections(); });
    SECTIONS.forEach(function (d) { d._rows.forEach(function (r) { mo.observe(r, { attributes: true, attributeFilter: ['style'] }); }); });
    if ($('userImportsStatus')) mo.observe($('userImportsStatus'), { childList: true, characterData: true, subtree: true });

    // pinned footer: the real buttons (ids + listeners kept)
    var btnRow = $('btnImportPreview') ? $('btnImportPreview').parentElement : null;
    var worldHint = btnRow && btnRow.nextElementSibling && btnRow.nextElementSibling.classList.contains('hint') ? btnRow.nextElementSibling : null;
    if (btnRow) {
        btnRow.classList.add('d2-foot-btns');
        var bImp = $('btnImportPreview'); if (bImp) { bImp.classList.add('d2-primary'); bImp.title = 'Choose an image, preview its shine, then save it (I)'; }
        var batchBtn = el('button', 'btn', 'Batch import…'); batchBtn.type = 'button'; batchBtn.id = 'd2BatchBtn';
        batchBtn.title = 'Pick many images: each one goes straight into your library (no preview step), one after another';
        batchBtn.addEventListener('click', pickBatch);
        btnRow.appendChild(batchBtn);
        railFoot.appendChild(btnRow);
        if (worldHint) { worldHint.classList.add('d2-foot-hint'); worldHint.innerHTML = 'Tip: hold <b>Shift</b> while dropping art for an instant Shokk the World.'; railFoot.appendChild(worldHint); }
    }

    // assemble the rail
    railScroll.appendChild(tile);
    railScroll.appendChild(typeSec);
    [secDna, secChan, secSet, secMix, secRec, secLib].forEach(function (d) { railScroll.appendChild(d); });
    if (newCard) { railScroll.appendChild(newCard); newCard.classList.add('d2-leftovers'); }
    aside.appendChild(railScroll); aside.appendChild(railFoot);
    syncChips(); syncSections();

    // ------------------------------------------------------------------ 1c. inspector: the selected drop or the pending import, always on screen
    var insp = el('section', 'd2-insp'); insp.id = 'd2Insp'; insp.setAttribute('aria-label', 'Drop preview'); insp.tabIndex = -1;
    insp.innerHTML =
        '<div class="d2-insp-head"><div class="d2-insp-titles"><div class="d2-insp-kicker" id="d2InspKicker">Preview</div>' +
        '<div class="d2-insp-title" id="d2InspTitle">Nothing selected</div></div>' +
        '<button type="button" class="d2-x" id="d2InspClose" title="Close (Esc)" aria-label="Close preview">×</button></div>' +
        '<div class="d2-insp-body" id="d2InspBody">' +
        '<div class="d2-insp-empty" id="d2InspEmpty"><p><b>Click a drop</b> to see its paint and shine here.</p>' +
        '<p>New art? Drop it anywhere on this window. Its preview opens here with a <b>Save to library</b> button.</p>' +
        '<ul class="d2-keys"><li><kbd>←↑↓→</kbd> move</li><li><kbd>Enter</kbd> open</li><li><kbd>Space</kbd> select</li><li><kbd>U</kbd> use on car</li>' +
        '<li><kbd>F</kbd> favourite</li><li><kbd>Del</kbd> delete</li><li><kbd>I</kbd> import</li><li><kbd>/</kbd> search</li><li><kbd>Esc</kbd> close</li></ul></div>' +
        '<div class="d2-pending" id="d2Pending" hidden><p class="d2-pending-msg">Not saved yet. Check the paint and shine below, then save it.</p></div>' +
        '<img class="d2-hero" id="d2Hero" alt="paint | spec preview" hidden>' +
        '<div class="d2-use" id="d2Use" hidden></div>' +
        '<div class="d2-insp-acts" id="d2InspActs"></div>' +
        '</div>';
    app.appendChild(insp);
    var inspBody = $('d2InspBody');
    ['userImportPreviewMeta', 'userImportPreviewActions', 'userImportPreviewBox'].forEach(function (id) { var e = $(id); if (e) inspBody.appendChild(e); });
    var pend = $('d2Pending'), pa = $('userImportPreviewActions');
    if (pa) {
        pend.appendChild(pa);
        var cbtn = pa.querySelector('button'); if (cbtn) { cbtn.classList.add('d2-primary'); cbtn.textContent = 'Save to library'; cbtn.title = 'Commit this drop: it joins your library and the Shokk Drop group in the Paint Booth'; }
        var disc = el('button', 'btn', 'Discard'); disc.type = 'button'; disc.title = 'Forget this preview (nothing was saved)';
        disc.addEventListener('click', function () { window._pendingUserImportFiles = null; window._pendingUserImportKind = null; pa.style.display = 'none'; var b = $('userImportPreviewBox'); if (b) b.innerHTML = ''; var m = $('userImportPreviewMeta'); if (m) m.textContent = ''; setMode('empty'); });
        pa.appendChild(disc);
        // [SPB-DROP2 2026-10-10] user-imports.js re-labels this button "Commit drop" on every preview (and the paint+spec set path
        // labels it "Commit set (exact finish)"), so the plain label is re-applied each time the bar shows. The onclick is never touched.
        var relabel = function () {
            var b = pa.querySelector('button'); if (!b) return;
            var t = b.textContent || '';
            if (t === 'Commit drop') b.textContent = 'Save to library';
            else if (t === 'Commit set (exact finish)') b.textContent = 'Save set to library';
        };
        new MutationObserver(function () { if (pa.style.display !== 'none') { relabel(); setMode('pending'); } else if (mode === 'pending') setMode(curId ? 'saved' : 'empty'); }).observe(pa, { attributes: true, attributeFilter: ['style'] });
        new MutationObserver(relabel).observe(pa, { childList: true, subtree: true, characterData: true });
    }
    var box = $('userImportPreviewBox');
    if (box) new MutationObserver(function () { if (box.innerHTML && mode === 'empty') setMode(pa && pa.style.display !== 'none' ? 'pending' : 'saved'); }).observe(box, { childList: true });
    var mode = 'empty', curId = null;
    function setMode(m) {
        mode = m;
        insp.classList.toggle('d2-mode-empty', m === 'empty'); insp.classList.toggle('d2-mode-pending', m === 'pending'); insp.classList.toggle('d2-mode-saved', m === 'saved');
        $('d2InspEmpty').hidden = m !== 'empty'; pend.hidden = m !== 'pending';
        $('d2Hero').hidden = m !== 'saved' || !$('d2Hero').src; $('d2Use').hidden = m !== 'saved'; $('d2InspActs').hidden = m !== 'saved';
        var kick = $('d2InspKicker'), title = $('d2InspTitle');
        if (m === 'empty') { kick.textContent = 'Preview'; title.textContent = 'Nothing selected'; }
        if (m === 'pending') { kick.textContent = 'New drop · preview'; title.textContent = window._pendingUserImportName || 'Your art'; }
        if (m !== 'empty') openInsp(); else root.classList.remove('d2-insp-open');
    }
    function openInsp() { root.classList.add('d2-insp-open'); }
    function closeInsp() {
        root.classList.remove('d2-insp-open');
        if (mode === 'saved') { doc.querySelectorAll('.drop-card-active').forEach(function (c) { c.classList.remove('drop-card-active'); }); curId = null; setMode('empty'); }
    }
    $('d2InspClose').addEventListener('click', function () { var back = curId && cardOf(curId); closeInsp(); if (back) back.focus(); });

    function cardOf(id) { return id ? doc.querySelector('.drop-card[data-drop-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]') : null; }
    // the card's own (hidden) action elements, in order, with plain labels
    var LABEL = [
        [/use in booth/i, 'Use on car', 'use'], [/^\.spbdrop$/i, 'Export .spbdrop', 'export'], [/copy link/i, 'Copy share link', 'link'],
        [/pipeline render/i, 'Engine render thumbnail', 'render'], [/re-dna/i, 'Re-bake shine (replaces)', 'rebake'], [/fork/i, 'Fork as a new drop', 'fork'],
        [/view on ball/i, 'View on ball', 'ball'], [/^delete$/i, 'Delete…', 'delete']];
    function actionsOf(card) {
        var out = []; if (!card) return out;
        var holder = card.querySelector('.d2-acts') || card.querySelector(':scope > div:last-of-type');
        if (holder) Array.prototype.forEach.call(holder.querySelectorAll('button, a'), function (b) {
            var t = txt(b).replace(/^[^\w.]+/, ''), hit = null;
            LABEL.forEach(function (L) { if (!hit && L[0].test(t)) hit = L; });
            out.push({ el: b, label: hit ? hit[1] : t, key: hit ? hit[2] : t.toLowerCase(), title: b.title || '' });
        });
        var fav = card.querySelector('.drop-fav-btn');
        if (fav) out.splice(out.length - 1, 0, { el: fav, label: txt(fav) === '★' ? '★ Unfavourite' : '☆ Favourite', key: 'fav', title: fav.title });
        return out;
    }
    function run(a, id) {
        if (a.key === 'use') return useOnCar(id);
        if (a.key === 'render') { var r = cardOf(id); var img = r && r.querySelector('img.thumb'); a.el.click(); if (img) { var once = function () { img.removeEventListener('load', once); if (curId === id) { $('d2Hero').src = img.src; } }; img.addEventListener('load', once); } return; }
        a.el.click();
    }
    function fillInspector(id) {
        var card = cardOf(id); curId = id;
        var name = card ? txt(card.querySelector('h2 span')) || id : id;
        var meta = card ? txt(card.querySelector('.meta')) : '';
        $('d2InspKicker').textContent = (meta.split('·')[0] || 'drop').replace('paint_monolithic', 'Paint finish').replace('spec_overlay', 'Spec overlay').replace('pattern', 'Pattern').trim();
        $('d2InspTitle').textContent = name; $('d2InspTitle').title = id;
        var thumb = card && card.querySelector('img.thumb');
        var hero = $('d2Hero'); if (thumb && thumb.src) { hero.src = thumb.src; hero.hidden = false; } else { hero.removeAttribute('src'); hero.hidden = true; }
        var list = actionsOf(card), use = list.filter(function (a) { return a.key === 'use'; })[0];
        renderUse(id, !!use);
        var host = $('d2InspActs'); host.innerHTML = '';
        list.forEach(function (a) {
            if (a.key === 'use') return;
            var b = el(a.el.tagName === 'A' ? 'a' : 'button', 'btn d2-act' + (a.key === 'delete' ? ' d2-danger' : ''), esc(a.label));
            if (a.el.tagName === 'A') { b.href = a.el.getAttribute('href'); if (a.el.hasAttribute('download')) b.setAttribute('download', ''); } else b.type = 'button';
            b.title = a.title; b.dataset.act = a.key;
            if (a.el.tagName !== 'A') b.addEventListener('click', function () { run(a, id); if (a.key === 'fav') setTimeout(function () { if (curId === id) fillInspector(id); }, 50); });
            host.appendChild(b);
        });
        setMode('saved');
    }

    // ------------------------------------------------------------------ 5b. Use on car (the booth that opened this page) - upgrade
    function booth() {
        try { var op = window.opener; if (op && !op.closed && op.location.origin === location.origin && (typeof op.assignFinishToSelected === 'function' || typeof op.applyFinishFromBrowser === 'function')) return op; } catch (e) {}
        return null;
    }
    function boothParts(op) {
        try { var p = op.SpbProCar && typeof op.SpbProCar.parts === 'function' ? op.SpbProCar.parts() : []; return (p || []).map(function (x) { return typeof x === 'string' ? x : (x && (x.name || x.id)) || ''; }).filter(Boolean).slice(0, 40); } catch (e) { return []; }
    }
    var lastTarget = 'zone', partsAsked = false;
    try { lastTarget = localStorage.getItem('spbDrop2Target') || 'zone'; } catch (e) {}
    function renderUse(id, can) {
        var u = $('d2Use'); u.innerHTML = '';
        if (!can) { u.hidden = true; u.dataset.can = '0'; return; }
        u.dataset.can = '1';
        var op = booth();
        var b = el('button', 'btn d2-primary d2-use-btn', op ? 'Use on car' : 'Open in Paint Booth'); b.type = 'button'; b.id = 'd2UseBtn';
        b.title = op ? 'Put this finish on your car in the Paint Booth that is already open (U)' : 'Opens the Paint Booth in a new tab with this drop on the active zone (U)';
        b.addEventListener('click', function () { useOnCar(id); });
        u.appendChild(b);
        if (op) {
            var s = el('select', 'd2-target'); s.id = 'd2Target'; s.setAttribute('aria-label', 'Where on the car');
            var opts = [['zone', 'on the selected zone'], ['new', 'as a new zone, whole car']].concat(boothParts(op).map(function (p) { return ['part:' + p, 'on the ' + p + ' (new zone)']; }));
            opts.forEach(function (o) { var x = el('option', '', esc(o[1])); x.value = o[0]; s.appendChild(x); });
            s.value = opts.some(function (o) { return o[0] === lastTarget; }) ? lastTarget : 'zone';
            s.addEventListener('change', function () { lastTarget = s.value; try { localStorage.setItem('spbDrop2Target', s.value); } catch (e) {} });
            u.appendChild(s);
            // no parts known yet: ask the booth's car map for its OFFLINE part list once (ensure(false) = no vision call), then refresh this menu
            if (opts.length === 2 && !partsAsked && op.SpbProCar && typeof op.SpbProCar.ensure === 'function') {
                partsAsked = true;
                try { Promise.resolve(op.SpbProCar.ensure(false)).then(function () { if (curId === id && boothParts(op).length) renderUse(id, true); }, function () {}); } catch (e) {}
            }
            u.appendChild(el('p', 'd2-use-hint', 'Goes to the Paint Booth that opened this page. Undo there with Ctrl+Z.'));
        } else {
            u.appendChild(el('p', 'd2-use-hint', 'Open Shokk Drop from the Paint Booth to send drops straight onto your car, a zone or a part.'));
        }
    }
    function useOnCar(id) {
        var op = booth(), t = $('d2Target') ? $('d2Target').value : 'zone';
        var name = txt(cardOf(id) && cardOf(id).querySelector('h2 span')) || id;
        if (!op) { if (typeof window.useDropInBooth === 'function') window.useDropInBooth(id); return Promise.resolve({ ok: true, via: 'new-tab' }); }
        var p = (typeof op.loadUserImports === 'function') ? Promise.resolve(op.loadUserImports()).catch(function () {}) : Promise.resolve();
        return p.then(function () {
            var where;
            if (t === 'zone') {
                if (typeof op.assignFinishToSelected === 'function') op.assignFinishToSelected(id); else op.applyFinishFromBrowser(null, null, id);
                where = 'the selected zone';
            } else {
                if (!op.SpbProZone || typeof op.SpbProZone.add !== 'function') throw new Error('this booth has no zone kit, use "selected zone"');
                var spec = { name: 'SHOKK DROP ' + name, finish: id, region: t === 'new' ? { everything: true } : { part: t.slice(5) } };
                if (typeof op.pushZoneUndo === 'function') { try { op.pushZoneUndo('SHOKK DROP: ' + name); } catch (e) {} }
                var r = op.SpbProZone.add(spec);
                if (!r || r.ok === false) throw new Error((r && r.warnings && r.warnings[0]) || 'the booth refused the zone');
                try { if (typeof op.renderZones === 'function') op.renderZones(); } catch (e) {}
                where = t === 'new' ? 'a new whole-car zone' : 'the ' + t.slice(5) + ' (new zone)';
            }
            try { if (typeof op.triggerPreviewRender === 'function') op.triggerPreviewRender(); } catch (e) {}
            try { op.focus(); } catch (e) {}
            toast('"' + name + '" is on ' + where + ' in your Paint Booth.', 'success');
            return { ok: true, via: 'opener', where: where };
        }).catch(function (err) { toast('Could not send it to the booth: ' + (err.message || err), 'error'); return { ok: false, error: String(err.message || err) }; });
    }
    window.spbDrop2UseOnCar = useOnCar;

    // hook the page's own card selection -> inspector (onclick="selectDropCard(...)" resolves the global at click time)
    var origSelect = window.selectDropCard;
    if (typeof origSelect === 'function') {
        window.selectDropCard = function (id, card) {
            var r = origSelect.apply(this, arguments);
            try { fillInspector(id); } catch (e) {}
            return r;
        };
    }

    // ------------------------------------------------------------------ 2. cards: hover bar + More menu over the card's own hidden actions
    var grid = $('galleryGrid');
    var menu = el('div', 'd2-menu'); menu.id = 'd2CardMenu'; menu.setAttribute('role', 'menu'); menu.hidden = true; doc.body.appendChild(menu);
    function openMenu(card, anchor) {
        var id = card.dataset.dropId; menu.innerHTML = '';
        actionsOf(card).forEach(function (a) {
            var b = el('button', 'd2-menu-item' + (a.key === 'delete' ? ' d2-danger' : ''), esc(a.label)); b.type = 'button'; b.setAttribute('role', 'menuitem'); b.title = a.title;
            b.addEventListener('click', function (e) { e.stopPropagation(); closeMenu(); run(a, id); });
            menu.appendChild(b);
        });
        var r = anchor.getBoundingClientRect(); menu.hidden = false;
        var mh = menu.offsetHeight, mw = menu.offsetWidth;
        menu.style.left = Math.max(8, Math.min(innerWidth - mw - 8, r.right - mw)) + 'px';
        menu.style.top = (r.bottom + mh + 8 > innerHeight ? Math.max(8, r.top - mh - 4) : r.bottom + 4) + 'px';
        menu._anchor = anchor; var f = menu.querySelector('button'); if (f) f.focus();
    }
    function closeMenu() { if (!menu.hidden) { menu.hidden = true; if (menu._anchor && doc.contains(menu._anchor)) menu._anchor.focus(); } }
    menu.addEventListener('keydown', function (e) {
        var items = Array.prototype.slice.call(menu.querySelectorAll('button')), i = items.indexOf(doc.activeElement);
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus(); }
        else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(); }
        else if (e.key === 'Tab') closeMenu();
    });
    doc.addEventListener('click', function (e) {
        if (!menu.hidden && !menu.contains(e.target)) closeMenu();
        if (!moreMenu.hidden && !moreMenu.contains(e.target) && e.target !== moreBtn) toggleMore(false);
    });
    function decorate() {
        if (!grid) return;
        grid.querySelectorAll('.drop-card:not([data-d2])').forEach(function (card) {
            card.setAttribute('data-d2', '1'); card.tabIndex = 0;
            var id = card.dataset.dropId, name = txt(card.querySelector('h2 span')) || id;
            card.setAttribute('aria-label', name);
            var holder = card.querySelector(':scope > div:last-of-type'); if (holder) holder.classList.add('d2-acts');
            var meta = card.querySelector('.meta'); if (meta) meta.textContent = txt(meta).replace(/^paint_monolithic/, 'Paint').replace(/^spec_overlay/, 'Spec overlay').replace(/^pattern/, 'Pattern').replace(/^car_template/, 'Whole car');
            var bar = el('div', 'd2-quick');
            var acts = actionsOf(card);
            if (acts.some(function (a) { return a.key === 'use'; })) {
                var u = el('button', 'd2-q d2-q-use', 'Use on car'); u.type = 'button'; u.tabIndex = -1; u.title = booth() ? 'Send to the open Paint Booth (U)' : 'Open in the Paint Booth (U)';
                u.addEventListener('click', function (e) { e.stopPropagation(); if (window.selectDropCard) window.selectDropCard(id, card); useOnCar(id); });
                bar._use = u;   // [SPB-DROP2 2026-10-10] sits on the thumbnail's bottom-right (no overlap with the type line)
            }
            var m = el('button', 'd2-q d2-q-more', '⋯'); m.type = 'button'; m.tabIndex = -1; m.title = 'All actions for this drop'; m.setAttribute('aria-label', 'More actions for ' + name);
            m.addEventListener('click', function (e) { e.stopPropagation(); if (!menu.hidden && menu._anchor === m) closeMenu(); else openMenu(card, m); });
            bar.appendChild(m);
            var th = card.querySelector('img.thumb'); if (th) th.insertAdjacentElement('afterend', bar); else card.appendChild(bar);
            if (bar._use) bar.insertAdjacentElement('afterend', bar._use);
            if (curId === id) card.classList.add('drop-card-active');
        });
        if (curId && !cardOf(curId) && mode === 'saved') { /* filtered out: keep the inspector, its actions still call the detached elements */ }
    }
    if (grid) { new MutationObserver(decorate).observe(grid, { childList: true }); decorate(); }

    // ------------------------------------------------------------------ 4. keyboard
    function cards() { return Array.prototype.slice.call(grid ? grid.querySelectorAll('.drop-card') : []); }
    function moveFocus(cur, key) {
        var list = cards(); if (!list.length) return;
        var i = list.indexOf(cur); if (i < 0) { list[0].focus(); return; }
        var top0 = list[0].offsetTop, cols = list.filter(function (c) { return c.offsetTop === top0; }).length || 1;
        var j = key === 'ArrowRight' ? i + 1 : key === 'ArrowLeft' ? i - 1 : key === 'ArrowDown' ? i + cols : i - cols;
        if (j >= 0 && j < list.length) { list[j].focus(); list[j].scrollIntoView({ block: 'nearest' }); }
    }
    if (grid) grid.addEventListener('keydown', function (e) {
        var card = e.target.closest && e.target.closest('.drop-card'); if (!card || e.target !== card) return;
        var id = card.dataset.dropId;
        if (['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].indexOf(e.key) >= 0) { e.preventDefault(); moveFocus(card, e.key); }
        else if (e.key === 'Enter') { e.preventDefault(); if (window.selectDropCard) window.selectDropCard(id, card); }
        else if (e.key === ' ') { e.preventDefault(); var cb = card.querySelector('.drop-pick'); if (cb) cb.click(); }
        else if (e.key === 'Delete') { e.preventDefault(); if (window.deleteShokkDropCard) window.deleteShokkDropCard(id); }
        else if ((e.key === 'f' || e.key === 'F') && !e.ctrlKey && !e.metaKey) { e.preventDefault(); var fb = card.querySelector('.drop-fav-btn'); if (fb) fb.click(); }
        else if ((e.key === 'u' || e.key === 'U') && !e.ctrlKey && !e.metaKey) { e.preventDefault(); if (actionsOf(card).some(function (a) { return a.key === 'use'; })) { if (window.selectDropCard) window.selectDropCard(id, card); useOnCar(id); } }
        else if (e.key === 'ContextMenu' || (e.shiftKey && e.key === 'F10')) { e.preventDefault(); var mb = card.querySelector('.d2-q-more'); if (mb) openMenu(card, mb); }
    });
    doc.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (!menu.hidden) { closeMenu(); return; }
            if (!moreMenu.hidden) { toggleMore(false); moreBtn.focus(); return; }
            if (window.SpbDialog && SpbDialog.isOpen && SpbDialog.isOpen()) return;
            if (doc.querySelector('.shokk-world-overlay, #shokkWorldOverlay') && shown(doc.querySelector('.shokk-world-overlay, #shokkWorldOverlay'))) return;
            if (root.classList.contains('d2-insp-open') && !typing(e.target)) { var back = curId && cardOf(curId); closeInsp(); if (back) back.focus(); }
            return;
        }
        if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
        if (window.SpbDialog && SpbDialog.isOpen && SpbDialog.isOpen()) return;
        if (e.key === '?') { e.preventDefault(); showKeys(); }
        else if ((e.key === 'i' || e.key === 'I') && !(e.target.closest && e.target.closest('.drop-card'))) { e.preventDefault(); tile.click(); }
        else if (['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].indexOf(e.key) >= 0 && (e.target === doc.body || e.target === doc.documentElement)) { e.preventDefault(); var l = cards(); if (l.length) l[0].focus(); }
    });
    function showKeys() {
        var m = 'Gallery: arrows move between drops, Enter opens one, Space selects it for bulk actions, U puts it on the car, F favourites it, Del deletes it (asks first), Shift+F10 opens its menu.\n' +
            'Anywhere: / search, Esc close, I import art, ? this list.\nDrag files anywhere on the window: preview and import, Shokk the World, batch import or add a .spbdrop pack.';
        if (window.SpbDialog && SpbDialog.notice) SpbDialog.notice('Keyboard Shortcuts', { message: m, nativeText: m }); else toast(m, 'info');
    }

    // ------------------------------------------------------------------ 3. drag anywhere -> one overlay with clear targets
    var ov = el('div', 'd2-drag');
    ov.id = 'd2Drag'; ov.hidden = true;
    ov.innerHTML = '<div class="d2-drag-inner"><div class="d2-drag-title" id="d2DragTitle">Drop to import</div><div class="d2-drag-targets" id="d2DragTargets"></div>' +
        '<div class="d2-drag-sub">Release over a box. Esc cancels.</div></div>';
    doc.body.appendChild(ov);
    var dragDepth = 0;
    function hasFiles(e) { try { return Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0; } catch (x) { return false; } }
    function targetsFor() {
        return [
            { k: 'preview', t: 'Preview, then save', s: 'One image: see its paint + shine first' },
            { k: 'world', t: 'Shokk the World', s: '20 shine variations of your art' },
            { k: 'batch', t: 'Batch import', s: 'Every image straight into the library' },
            { k: 'pack', t: 'Add .spbdrop pack', s: 'Drops shared by a friend' }];
    }
    function buildTargets() {
        var host = $('d2DragTargets'); host.innerHTML = '';
        targetsFor().forEach(function (t) {
            var d = el('div', 'd2-drag-t', '<b>' + esc(t.t) + '</b><span>' + esc(t.s) + '</span>'); d.dataset.k = t.k; host.appendChild(d);
            d.addEventListener('dragover', function (e) { e.preventDefault(); host.querySelectorAll('.d2-drag-t').forEach(function (x) { x.classList.toggle('hot', x === d); }); });
        });
    }
    buildTargets();
    function hideDrag() { dragDepth = 0; ov.hidden = true; root.classList.remove('d2-dragging'); }
    window.addEventListener('dragenter', function (e) { if (!hasFiles(e)) return; dragDepth++; if (ov.hidden) { ov.hidden = false; root.classList.add('d2-dragging'); ov.querySelectorAll('.hot').forEach(function (x) { x.classList.remove('hot'); }); } });
    window.addEventListener('dragleave', function (e) { if (!hasFiles(e)) return; dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth || e.clientX <= 0 || e.clientY <= 0 || e.clientX >= innerWidth || e.clientY >= innerHeight) { if (!e.relatedTarget) hideDrag(); } });
    window.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !ov.hidden) hideDrag(); });
    ov.addEventListener('dragover', function (e) { e.preventDefault(); try { e.dataTransfer.dropEffect = 'copy'; } catch (x) {} });
    ov.addEventListener('drop', function (e) {
        e.preventDefault(); e.stopPropagation();
        var t = e.target.closest ? e.target.closest('.d2-drag-t') : null, k = t ? t.dataset.k : 'preview';
        var files = Array.prototype.slice.call((e.dataTransfer && e.dataTransfer.files) || []); hideDrag();
        routeFiles(files, e.shiftKey ? 'world' : k);
    });
    function isImg(f) { return /\.(png|jpe?g|webp|tga|bmp)$/i.test(f.name) || (f.type || '').indexOf('image/') === 0; }
    function isPack(f) { var n = (f.name || '').toLowerCase(); return n.endsWith('.spbdrop') || n.endsWith('.spbshokk'); }
    function routeFiles(files, k) {
        var imgs = files.filter(isImg), packs = files.filter(isPack);
        if (packs.length && (k === 'pack' || !imgs.length)) return importPacks(packs);
        if (!imgs.length) { toast(packs.length ? 'Drop .spbdrop packs on "Add .spbdrop pack"' : 'That file type isn’t importable: PNG / JPG / WebP art or .spbdrop packs', 'info'); return; }
        if (k === 'pack') { toast('Those are images, not .spbdrop packs: importing them with a preview instead', 'info'); k = 'preview'; }
        if (k === 'world' && typeof window.startShokkTheWorld === 'function') return window.startShokkTheWorld(imgs);
        if (k === 'batch') return batchImport(imgs);
        if (imgs.length > 1) { toast(imgs.length + ' images: importing them as a batch (one preview at a time is for single images)', 'info'); return batchImport(imgs); }
        if (typeof window.processUserImportFileList === 'function') return window.processUserImportFileList(imgs, true);
    }
    window.spbDrop2RouteFiles = routeFiles;
    function importPacks(packs) {
        if (typeof window.importUserImportPack !== 'function') { toast('Pack import unavailable: reload the page', 'error'); return; }
        toast('Importing ' + packs.length + ' pack(s)…', 'info');
        return Promise.all(packs.map(window.importUserImportPack)).then(function (results) {
            var n = 0; (results || []).forEach(function (r) { n += ((r && r.imported) || []).length; });
            toast('Imported ' + (n || packs.length) + ' drop(s)', 'success');
            if (typeof window.loadUserImports === 'function') window.loadUserImports();
        }).catch(function (err) { toast('Pack import failed: ' + err.message, 'error'); });
    }

    // ------------------------------------------------------------------ 5a. batch import (upgrade): many images, one after another, with progress
    var batchPanel = el('div', 'd2-batch'); batchPanel.id = 'd2Batch'; batchPanel.hidden = true; batchPanel.setAttribute('aria-live', 'polite'); doc.body.appendChild(batchPanel);
    var batchState = null;
    function pickBatch() {
        var inp = doc.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.accept = 'image/png,image/jpeg,image/webp,.tga,.bmp';
        inp.onchange = function () { var f = Array.prototype.slice.call(inp.files || []); if (f.length) batchImport(f); };
        inp.click();
    }
    function batchImport(files) {
        files = files.filter(isImg);
        if (!files.length) return Promise.resolve({ ok: 0, failed: 0 });
        if (batchState && batchState.running) { batchState.queue = batchState.queue.concat(files); paintBatch(); toast('Added ' + files.length + ' to the batch', 'info'); return batchState.promise; }
        if (kindSel && (kindSel.value === 'paint_spec_set')) { kindSel.value = 'paint_monolithic'; kindSel.dispatchEvent(new Event('change', { bubbles: true })); toast('Batch import uses Type "Paint" (a paint + spec set needs its own maps)', 'info'); }
        batchState = { queue: files.slice(), rows: [], running: true, ok: 0, failed: 0, cancel: false };
        batchState.rows = files.map(function (f) { return { name: f.name, st: 'queued' }; });
        batchPanel.hidden = false; paintBatch();
        var proc = window.processUserImportFileList;
        var i = 0;
        function next() {
            if (batchState.cancel || i >= batchState.queue.length) return Promise.resolve();
            var f = batchState.queue[i], row = batchState.rows[i] || (batchState.rows[i] = { name: f.name, st: 'queued' });
            row.st = 'importing'; paintBatch(); i++;
            var base = f.name.replace(/\.[^.]+$/, '');
            return Promise.resolve().then(function () { return proc([f], false, base); })
                .then(function () { row.st = 'done'; batchState.ok++; }, function (err) { row.st = 'failed'; row.err = String(err && err.message || err); batchState.failed++; })
                .then(function () { paintBatch(); return next(); });
        }
        batchState.promise = next().then(function () {
            batchState.running = false; paintBatch();
            toast('Batch import: ' + batchState.ok + ' added' + (batchState.failed ? ', ' + batchState.failed + ' failed' : '') + (batchState.cancel ? ' (stopped)' : ''), batchState.failed ? 'error' : 'success');
            return { ok: batchState.ok, failed: batchState.failed };
        });
        return batchState.promise;
    }
    function paintBatch() {
        if (!batchState) return;
        var n = batchState.rows.length, done = batchState.ok + batchState.failed;
        var ICON = { queued: '·', importing: '…', done: '✓', failed: '✕' };
        batchPanel.innerHTML = '<div class="d2-batch-head"><b>Batch import</b> <span>' + done + ' / ' + n + '</span>' +
            (batchState.running ? '<button type="button" class="btn d2-batch-stop">Stop after this one</button>' : '<button type="button" class="btn d2-batch-close">Close</button>') + '</div>' +
            '<div class="d2-batch-bar"><i style="width:' + (n ? Math.round(done / n * 100) : 0) + '%"></i></div>' +
            '<ol class="d2-batch-list">' + batchState.rows.map(function (r) { return '<li class="st-' + r.st + '" title="' + esc(r.err || '') + '"><span>' + ICON[r.st] + '</span>' + esc(r.name) + '</li>'; }).join('') + '</ol>';
        var s = batchPanel.querySelector('.d2-batch-stop'); if (s) s.addEventListener('click', function () { batchState.cancel = true; s.disabled = true; s.textContent = 'Stopping…'; });
        var c = batchPanel.querySelector('.d2-batch-close'); if (c) c.addEventListener('click', function () { batchPanel.hidden = true; });
    }
    window.spbDrop2BatchImport = batchImport;

    // ------------------------------------------------------------------ onboarding: compact strip (all of its buttons kept)
    var ob = $('shokkDropOnboarding'); if (ob) ob.classList.add('d2-onboard');
    // [SPB-DROP2 2026-10-10] one word for one action: the button reads "Save to library", so the guide step and the
    // "Preview ready" toast from user-imports.js say the same (text only; the old page keeps "Commit" with the kill switch on).
    if (ob) [].forEach.call(ob.querySelectorAll('.onboard-step strong'), function (s) { if (/^Preview, then Commit$/.test(s.textContent)) s.textContent = 'Preview, then Save'; });
    if (typeof window.showToast === 'function' && !window.showToast.__d2) {
        var _st = window.showToast;
        window.showToast = function (m) { var a = [].slice.call(arguments); if (typeof m === 'string') a[0] = m.replace('Click Commit drop.', 'Click Save to library.'); return _st.apply(this, a); };
        window.showToast.__d2 = 1;
    }

    // ------------------------------------------------------------------ a saved drop shows up at once
    // [SPB-DROP2 2026-10-10] found by t_e2e: after "Commit drop" the old page refreshed only the rail list (user-imports.js calls its own
    // loadUserImports closure, not the gallery-refreshing window wrapper), so the new drop was missing from the gallery until a reload and
    // the spent Commit button stayed up (a 2nd click opened a file picker). The status line ("N drop(s) · ...") changes whenever the
    // library count changes -> refresh the gallery (an unchanged list costs one JSON fetch and no re-render, see refreshGallery) and, after
    // a single save, close the spent preview bar and open the new drop in the inspector. Batch keeps its own panel and selection.
    (function () {
        var st = $('userImportsStatus'); if (!st || typeof window.retryShokkDropGallery !== 'function') return;
        function num() { var m = /^(\d+) drop/.exec(st.textContent || ''); return m ? +m[1] : null; }
        var lastN = num();
        new MutationObserver(function () {
            var n = num(); if (n === null || n === lastN) return;
            var grew = lastN !== null && n > lastN; lastN = n;
            var known = {}; [].forEach.call(document.querySelectorAll('#galleryGrid .drop-card'), function (c) { known[c.dataset.dropId] = 1; });
            window.retryShokkDropGallery();
            if (!grew || (batchState && batchState.running)) return;
            var pa = $('userImportPreviewActions');
            var tries = 0;
            (function look() {
                var fresh = [].filter.call(document.querySelectorAll('#galleryGrid .drop-card'), function (c) { return !known[c.dataset.dropId]; });
                if (!fresh.length) { if (++tries < 24) setTimeout(look, 250); return; }
                if (pa && !window._pendingUserImportFiles && pa.style.display !== 'none') pa.style.display = 'none';
                var c = fresh[fresh.length - 1];
                setTimeout(function () {   // after the preview-bar observer has left 'pending' (MutationObserver callbacks are microtasks)
                    if (mode !== 'pending' && window.selectDropCard) { window.selectDropCard(c.dataset.dropId, c); try { c.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
                }, 30);
            })();
        }).observe(st, { childList: true, characterData: true, subtree: true });
    })();

    // done: show the page (html.d2-boot hid it while the shell was built; a 2.5 s failsafe in the <head> also reveals it)
    root.classList.remove('d2-boot');
})();
