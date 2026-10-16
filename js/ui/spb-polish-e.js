/* [SPB-UI-POLISH-E 2026-10-10] wave 5 of the "make it look like a real product" pass: the header's first row. Presentation + small DOM wrappers only; no behaviour changes.
   1. File chips. #paintFile (Source Paint) and #outputDir (iRacing Car Folder) were raw, truncated path text boxes ("C:\DRIVE E BACKU"). Each now
      shows a calm chip: line icon + the file / folder NAME, the full path in the tooltip. A click (or Tab / any programmatic focus) swaps the chip for
      the very same input, so typing, pasting, the recent-paths list and Enter-to-commit work exactly as before. The input element, its id and every
      handler stay where they were; the chip only mirrors its value (value setter hook + input / change events, so code that does `el.value = path`
      updates the chip too).
   2. Open Paint... The two jargon buttons (TGA/PNG/JPEG, PSD/XCF/ORA) are wrapped in one menu opened by a single "Open Paint..." button. The original
      buttons are NOT replaced: the same nodes (same onclick, data-testid, tooltips) now live inside the menu, so everything that clicks them still works.
   3. Car group. iRacing User ID + the Custom / Sim-Stamped Number checkboxes become one "Car" group: a pill holding the ID, and a two-segment control
      for the number mode (the checkboxes stay, visually hidden inside their labels; their handlers are untouched). Long words become short at narrow widths.
   Everything is styled by the [SPB-UI-POLISH-E] CSS block. Kill switch: body.spb-polish-e-off (CSS) restores the wave-D look, body.spb-polish-off removes all waves;
   the added nodes are display:none without the CSS, so the old inputs and buttons show again. */
(function () {
    'use strict';
    if (window.__spbPolishE) return;
    window.__spbPolishE = true;
    var doc = document;

    function el(tag, cls, attrs) {
        var e = doc.createElement(tag);
        if (cls) e.className = cls;
        if (attrs) for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]);
        return e;
    }
    function baseName(p) {
        var s = String(p || '').trim().replace(/[\\\/]+$/, '');
        if (!s) return '';
        var i = Math.max(s.lastIndexOf('\\'), s.lastIndexOf('/'));
        return i >= 0 ? s.slice(i + 1) : s;
    }

    /* ---------------- 1. file chips ---------------- */
    var CHIPS = [
        { input: 'paintFile', id: 'peChipPaint', icon: 'file', empty: 'No paint file open', tip: 'Source Paint', how: 'Click to type or paste a path. Use Open Paint to browse.' },
        { input: 'outputDir', id: 'peChipFolder', icon: 'folder', empty: 'Choose the car folder', tip: 'iRacing Car Folder', how: 'Click to type or paste a path. Use the buttons beside it to pick a detected car or browse.' }
    ];

    function hookValue(input, cb) {
        // Mirror programmatic `input.value = x` (the app does this in a dozen places) without touching those callers.
        try {
            var d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
            if (!d || !d.get || !d.set) return;
            Object.defineProperty(input, 'value', {
                configurable: true, enumerable: d.enumerable,
                get: function () { return d.get.call(this); },
                set: function (v) { d.set.call(this, v); try { cb(); } catch (e) {} }
            });
        } catch (e) {}
    }

    function buildChip(c) {
        var input = doc.getElementById(c.input);
        if (!input || input.getAttribute('data-pe-chip') === '1') return;
        var row = input.parentNode;
        if (!row) return;
        var chip = el('button', 'pe-chip', { type: 'button', id: c.id, 'data-pe-for': c.input });
        var ic = el('span', 'pe-ic pe-ic-' + c.icon, { 'aria-hidden': 'true' });
        var nm = el('span', 'pe-nm');
        chip.appendChild(ic); chip.appendChild(nm);
        row.insertBefore(chip, input);
        input.setAttribute('data-pe-chip', '1');
        row.classList.add('pe-chipped');

        function sync() {
            var v = String(input.value || '').trim();
            // [2026-10-13 owner: "PSD showing as PSD.tga under SOURCE PAINT"] a layered import (PSD/XCF/ORA) stores its path in #paintFile with the
            // extension swapped to .tga (paint-booth-3-canvas.js commit step; renders upload the layer composite, other code keys on the .tga form).
            // The chip shows the file the buyer actually opened; the stored value is unchanged.
            var lp = String(window._psdPath || '').trim();
            if (c.input === 'paintFile' && window._psdLayersLoaded && lp && /\.tga$/i.test(v)
                && lp.replace(/\.(psd|ora|xcf)$/i, '.tga').replace(/\\/g, '/').toLowerCase() === v.replace(/\\/g, '/').toLowerCase()) v = lp;
            var name = baseName(v);
            nm.textContent = name || c.empty;
            chip.classList.toggle('pe-empty', !name);
            chip.title = (v ? c.tip + ': ' + v : c.tip + ': none yet') + '\n' + c.how;
            chip.setAttribute('aria-label', c.tip + ': ' + (name || 'not set') + '. Press to edit the path.');
        }
        hookValue(input, function () { sync(); setTimeout(sync, 0); });   // deferred pass: the layered import publishes window._psdPath just AFTER it sets the value
        input.addEventListener('input', sync);
        input.addEventListener('change', sync);
        sync();

        function edit() { row.classList.add('pe-editing'); }
        function done() { row.classList.remove('pe-editing'); sync(); }
        chip.addEventListener('click', function () { input.focus(); try { input.select(); } catch (e) {} });
        input.addEventListener('focus', edit);
        input.addEventListener('blur', function () { setTimeout(function () { if (doc.activeElement !== input) done(); }, 0); });
        input.addEventListener('keydown', function (e) { if (e.key === 'Escape') { input.blur(); } });

        // the path check mark / cross (#paintPathStatus) tints the chip too
        var st = doc.getElementById('paintPathStatus');
        if (c.input === 'paintFile' && st && window.MutationObserver) {
            var upd = function () { chip.classList.toggle('pe-bad', /invalid/.test(st.className)); };
            new MutationObserver(upd).observe(st, { attributes: true, attributeFilter: ['class'] });
            upd();
        }
    }

    /* ---------------- 2. Open Paint... menu ---------------- */
    function buildOpenPaint() {
        if (doc.getElementById('peOpenPaint')) return;
        var row = doc.querySelector('.field-source .header-field-row');
        if (!row) return;
        var tga = row.querySelector('[data-testid="btn-browse-paint"]');
        var psd = row.querySelector('[data-testid="btn-import-psd"]');
        if (!tga || !psd) return;
        var wrap = el('div', 'pe-openpaint', { id: 'peOpenPaint' });
        var btn = el('button', 'pe-openpaint-btn', {
            type: 'button', id: 'peOpenPaintBtn', 'aria-haspopup': 'menu', 'aria-expanded': 'false', 'aria-controls': 'peOpenPaintMenu',
            title: 'Open your car\'s paint: a layered PSD, XCF or ORA template (keeps every layer) or a flat TGA, PNG or JPEG image.'
        });
        btn.textContent = 'Open Paint\u2026';
        var menu = el('div', 'pe-openpaint-menu', { id: 'peOpenPaintMenu', role: 'menu', 'aria-label': 'Open paint' });
        row.insertBefore(wrap, tga);
        wrap.appendChild(btn); wrap.appendChild(menu);
        menu.appendChild(psd); menu.appendChild(tga);          // the same nodes, same handlers
        psd.setAttribute('role', 'menuitem'); tga.setAttribute('role', 'menuitem');

        function items() { return [psd, tga]; }
        function place() {
            var r = btn.getBoundingClientRect();
            var w = Math.max(250, menu.offsetWidth || 250);
            menu.style.top = Math.round(r.bottom + 4) + 'px';
            menu.style.left = Math.round(Math.max(8, Math.min(r.left, window.innerWidth - w - 8))) + 'px';
        }
        function onDoc(e) { if (!wrap.contains(e.target)) close(false); }
        function onKey(e) {
            if (e.key === 'Escape') { close(true); e.preventDefault(); return; }
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                var its = items(), i = its.indexOf(doc.activeElement);
                i = e.key === 'ArrowDown' ? (i + 1) % its.length : (i <= 0 ? its.length - 1 : i - 1);
                its[i].focus(); e.preventDefault();
            }
        }
        function open(focusFirst) {
            wrap.classList.add('pe-open'); btn.setAttribute('aria-expanded', 'true');
            place();
            doc.addEventListener('mousedown', onDoc, true);
            doc.addEventListener('keydown', onKey, true);
            window.addEventListener('resize', onResize);
            if (focusFirst) psd.focus();
        }
        function onResize() { place(); }
        function close(refocus) {
            wrap.classList.remove('pe-open'); btn.setAttribute('aria-expanded', 'false');
            doc.removeEventListener('mousedown', onDoc, true);
            doc.removeEventListener('keydown', onKey, true);
            window.removeEventListener('resize', onResize);
            if (refocus) btn.focus();
        }
        btn.addEventListener('click', function () { if (wrap.classList.contains('pe-open')) close(false); else open(false); });
        btn.addEventListener('keydown', function (e) { if (e.key === 'ArrowDown') { e.preventDefault(); open(true); } });
        // picking an item: let its own onclick run first, then close
        menu.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.header-browse-btn')) setTimeout(function () { close(false); }, 0); });
        window.peCloseOpenPaint = function () { close(false); };
    }

    /* ---------------- 3. Car group ---------------- */
    function wrapWords(label, parts) {
        // parts: [[text, cls|null], ...]; rewrites ONLY the label's own text node, textContent stays identical
        if (!label || label.getAttribute('data-pe-seg') === '1') return;
        var tn = null;
        for (var i = 0; i < label.childNodes.length; i++) { var n = label.childNodes[i]; if (n.nodeType === 3 && /\S/.test(n.nodeValue)) { tn = n; break; } }
        if (!tn) return;
        var want = parts.map(function (p) { return p[0].replace(/\u00a0/g, ' '); }).join('');
        if (tn.nodeValue.replace(/\s+/g, ' ').trim() !== want.trim()) return;      // unexpected text: leave it alone
        var frag = doc.createDocumentFragment();
        parts.forEach(function (p) {
            if (p[1]) { var s = el('span', p[1]); s.textContent = p[0]; frag.appendChild(s); }
            else frag.appendChild(doc.createTextNode(p[0]));
        });
        label.replaceChild(frag, tn);
        label.setAttribute('data-pe-seg', '1');
    }
    function buildCar() {
        var box = doc.getElementById('iracingIdContainer');
        if (!box || box.getAttribute('data-pe-car') === '1') return;
        var input = doc.getElementById('iracingId');
        var lbl = box.querySelector('label[for="iracingId"]');
        var mode = box.querySelector('.header-number-mode');
        if (!input || !lbl || !mode) return;
        var inner = input.parentNode;
        var cap = el('span', 'pe-cap', { 'aria-hidden': 'true' });
        cap.textContent = 'Car';
        box.insertBefore(cap, box.firstChild);
        var pill = el('span', 'pe-idpill');
        inner.insertBefore(pill, input);
        pill.appendChild(lbl); pill.appendChild(input);
        inner.classList.add('pe-carrow');
        box.setAttribute('role', 'group'); box.setAttribute('aria-label', 'Car');
        // visible words: "iRacing User ID" -> "iRacing ID" -> "ID" as space gets short (the hidden words stay readable by screen readers)
        wrapWords(lbl, [['iRacing ', 'pe-id1'], ['User ', 'pe-id2'], ['ID', null]]);
        var cu = doc.getElementById('useCustomNumberCheckbox'), ss = doc.getElementById('useSimStampedCheckbox');
        if (cu) wrapWords(cu.parentNode, [['Custom', null], ['\u00a0Number', 'pe-num']]);
        if (ss) wrapWords(ss.parentNode, [['Sim', null], ['-Stamped', 'pe-lg'], ['\u00a0Number', 'pe-num']]);
        box.setAttribute('data-pe-car', '1');
    }

    function build() {
        try { CHIPS.forEach(buildChip); } catch (e) {}
        try { buildOpenPaint(); } catch (e) {}
        try { buildCar(); } catch (e) {}
        if (doc.body) doc.body.classList.add('pe-ready');
    }

    build();
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', build);
    window.addEventListener('load', build);
})();
