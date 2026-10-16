/* numbers-ui.js - [SPB-REV-NUMBERS 2026-10-10] the Number Kit dialog (js/rev/numbers/numbers-core.js does the work).
 * Entry points: Symmetry > Number Kit...  and  a Text-tool click on a number the kit made (re-opens it).
 * The dialog is a fixed-position panel (nothing in the layout moves when it opens). Typing / changing any control re-renders every place
 * live as real layers; Add Number Kit commits them as ONE undo step; Esc or Cancel takes them back off the car.
 * Kill switch: window.SPB_REV_NUMBERS_OFF (see core).
 */
(function (root) {
    'use strict';
    var doc = root.document, N = null, TAG = '[SPB-REV-NUMBERS]';
    if (root.SpbRevNumbersUI) return;
    function core() { return root.SpbRevNumbers; }
    function off() { return !core() || core().off(); }
    function warn(w, e) { try { console.warn(TAG, w, e && e.message || e); } catch (_) {} }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k); } catch (_) {} }
    // [SPB-TICKETS-2 2026-10-10] kill switches: SPB_TICKETS2_OFF (all) or SPB_T2_<id>_OFF (IQ26 = Style row fits the panel, IQ22 = flat-file note). window flag or localStorage = '1'.
    function t2Off(id) {
        var n = ['SPB_TICKETS2_OFF', 'SPB_T2_' + id + '_OFF'], i, v;
        for (i = 0; i < n.length; i++) { try { v = root[n[i]]; if (v === true || v === 1 || v === '1' || v === 'true') return true; v = root.localStorage && root.localStorage.getItem(n[i]); if (v === '1' || v === 'true') return true; } catch (e) { /* storage blocked */ } }
        return false;
    }
    // [TICKETS-4 2026-10-10] kill switches: SPB_T4_OFF (all) or SPB_T4_<n>_OFF (n = 5: the existing-numbers notice above Places). window flag or localStorage = '1'.
    function t4Off(n) {
        var k = ['SPB_T4_OFF', 'SPB_T4_' + n + '_OFF'], i, v;
        for (i = 0; i < k.length; i++) { try { v = root[k[i]]; if (v === true || v === 1 || v === '1' || v === 'true') return true; v = root.localStorage && root.localStorage.getItem(k[i]); if (v === '1' || v === 'true') return true; } catch (e) { /* storage blocked */ } }
        return false;
    }
    /** [IQ2-2] true while the paint is a flat file (TGA / PNG / JPEG: no layer tree): its pixels may already carry baked-in numbers. */
    function flatSource() {
        try {
            var L = (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; if (!Array.isArray(L)) return false;
            if (L.some(function (l) { return l && l.flatBackground === true; })) return true;      // FLAT-WIPE's locked Background = the flat pixels under the added layers
            var loaded = (typeof _psdLayersLoaded !== 'undefined') && !!_psdLayersLoaded, psd = (typeof _psdPath !== 'undefined' && !!_psdPath) || (typeof _psdData !== 'undefined' && !!_psdData);
            return L.length === 0 && !loaded && !psd && typeof paintImageData !== 'undefined' && !!paintImageData;
        } catch (e) { return false; }
    }
    function $(sel, el) { return (el || panel || doc).querySelector(sel); }

    var ICON = {
        hash: '<path d="M5 9h14"/><path d="M5 15h14"/><path d="m10 4-2 16"/><path d="m16 4-2 16"/>',
        x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
        alert: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
        refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>'
    };
    function svg(k, sz) { return '<svg class="spb-nk-svg" viewBox="0 0 24 24" width="' + (sz || 14) + '" height="' + (sz || 14) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

    var panel = null, S = null, raf = 0, LS = 'spb_rev_numbers_last_v1';
    function loadLast() { try { return JSON.parse(root.localStorage.getItem(LS) || 'null'); } catch (e) { return null; } }
    function saveLast(k) { try { root.localStorage.setItem(LS, JSON.stringify(k)); } catch (e) {} }
    function posLoad() { try { return JSON.parse(root.localStorage.getItem(LS + '_pos') || 'null'); } catch (e) { return null; } }
    function posSave(p) { try { root.localStorage.setItem(LS + '_pos', JSON.stringify(p)); } catch (e) {} }

    // ------------------------------------------------------------------ panel
    function row(label, inner, cls) { return '<div class="spb-nk-row' + (cls ? ' ' + cls : '') + '"><label>' + label + '</label>' + inner + '</div>'; }
    function colour(k, t) { return '<input type="color" data-k="' + k + '" title="' + t + '" aria-label="' + t + '">'; }
    function numIn(k, lo, hi, st, t, w) { return '<input type="number" data-k="' + k + '" min="' + lo + '" max="' + hi + '" step="' + st + '" title="' + t + '" aria-label="' + t + '"' + (w ? ' style="width:' + w + 'px"' : '') + '>'; }
    function buildPanel() {
        if (panel && panel.isConnected) return panel;
        var fonts = core().fonts().map(function (f) { return '<option value="' + esc(f) + '">' + esc(f) + '</option>'; }).join('');
        panel = doc.createElement('div'); panel.id = 'spbNumKit'; panel.className = 'spb-nk-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Number Kit');
        // [TICKETS-4 2026-10-10 item 5] the 'This car already has numbers' notice + Replace/Add choice sat below Turn Each Place: at 1100x800 it was cut off under the footer. It now sits ABOVE Places (always on screen). Kill switch: SPB_T4_OFF / SPB_T4_5_OFF (window flag or localStorage '1') puts it back below.
        var existHtml = '<div class="spb-nk-exist" hidden><div class="spb-nk-exist-t"></div><div class="spb-nk-seg" role="group" aria-label="Existing numbers">' +
                '<button type="button" data-rep="replace" aria-pressed="true">Replace Existing</button><button type="button" data-rep="add" aria-pressed="false">Add Alongside</button></div></div>', existTop = !t4Off(5);
        panel.innerHTML =
            '<div class="spb-nk-ph" data-drag="1"><span class="spb-nk-pt">' + svg('hash') + '<span class="spb-nk-title">Number Kit</span></span>' +
                '<button type="button" class="spb-nk-x" data-act="cancel" title="Close without adding (Esc)" aria-label="Close">' + svg('x', 12) + '</button></div>' +
            '<div class="spb-nk-thumbwrap"><canvas class="spb-nk-thumb" width="312" height="52" aria-hidden="true"></canvas></div>' +
            row('Number', '<input type="text" data-k="number" maxlength="4" autocomplete="off" spellcheck="false" inputmode="text" style="width:64px;text-align:center" title="The car number (1 to 4 letters or digits)" aria-label="Car number">' +
                '<select data-k="font" title="Font (the same fonts as the Text tool)" aria-label="Font" style="flex:1;min-width:0">' + fonts + '</select>') +
            row('Style', '<label class="spb-nk-chk" title="Bold"><input type="checkbox" data-k="bold">Bold</label><label class="spb-nk-chk" title="Italic"><input type="checkbox" data-k="italic">Italic</label>' +
                '<span class="spb-nk-sub">Slant</span>' + numIn('slant', 0, 25, 1, 'Slant the number (degrees)', 44) + '<span class="spb-nk-sub">Gap</span>' + numIn('spacing', -10, 40, 1, 'Space between the digits (% of the number size)', 44), t2Off('IQ26') ? '' : 'spb-nk-rowfit') +      // [SPB-TICKETS-2 2026-10-10 IQ2-6] the Gap field sat 21 px past the panel edge (row 350 px wide in a 329 px inner width): this class tightens the row (CSS REV-NUMBERS block)
            row('Fill', colour('fill', 'Number colour')) +
            row('Outline 1', colour('ring1c', 'First outline colour') + numIn('ring1w', 0, 25, 0.5, 'First outline thickness (% of the number size, 0 = none)', 52) + '<span class="spb-nk-unit">%</span>') +
            row('Outline 2', colour('ring2c', 'Second outline colour') + numIn('ring2w', 0, 25, 0.5, 'Second (outer) outline thickness (% of the number size, 0 = none)', 52) + '<span class="spb-nk-unit">%</span>') +
            row('Shadow', '<input type="checkbox" data-k="shon" title="Drop shadow" aria-label="Drop shadow">' + colour('shc', 'Shadow colour') + '<span class="spb-nk-sub">Dist</span>' + numIn('shd', 0, 20, 0.5, 'Shadow distance (% of the number size)', 44) +
                '<span class="spb-nk-sub">Soft</span>' + numIn('shs', 0, 12, 0.5, 'Shadow softness (% of the number size)', 44)) +
            row('Panel', '<input type="checkbox" data-k="plon" title="A number panel behind the number" aria-label="Number panel">' +
                '<select data-k="plshape" title="Panel shape" aria-label="Panel shape"><option value="rounded">Rounded Box</option><option value="oval">Oval</option><option value="circle">Circle</option><option value="square">Square</option></select>' +
                colour('plc', 'Panel colour') + colour('plb', 'Panel border colour')) +
            (existTop ? existHtml : '') +
            row('Places', '<div class="spb-nk-places" role="group" aria-label="Places">' +
                '<button type="button" class="spb-nk-chip" data-place="left" aria-pressed="false" title="Number on the left door">Left Door</button>' +
                '<button type="button" class="spb-nk-chip" data-place="right" aria-pressed="false" title="Number on the right door">Right Door</button>' +
                '<button type="button" class="spb-nk-chip" data-place="roof" aria-pressed="false" title="Number on the roof">Roof</button></div>') +
            row('Roof', '<select data-k="roofFrom" title="Which way the roof number reads" aria-label="Roof reading side"><option value="driver">Reads From Driver’s Side</option><option value="passenger">Reads From Passenger’s Side</option></select>') +
            row('Size', '<input type="range" data-k="size" min="30" max="140" step="1" aria-label="Size"><span class="spb-nk-val" data-val="size"></span>') +
            row('Material', '<select data-k="material" title="Spec material for the number (Layer Materials)" aria-label="Material"><option value="none">None</option><option value="chrome">Chrome Foil</option><option value="gloss">Gloss Vinyl</option><option value="satin">Satin Vinyl</option><option value="matte">Matte Vinyl</option></select>', 'spb-nk-matrow') +
            '<details class="spb-nk-adv"><summary>Turn Each Place</summary>' +
                row('Left Door', '<select data-k="turnleft" aria-label="Left door turn"><option value="auto">Auto</option><option value="0">Upright</option><option value="90">90° Clockwise</option><option value="180">Upside Down</option><option value="270">90° Counter-Clockwise</option></select>') +
                row('Right Door', '<select data-k="turnright" aria-label="Right door turn"><option value="auto">Auto</option><option value="0">Upright</option><option value="90">90° Clockwise</option><option value="180">Upside Down</option><option value="270">90° Counter-Clockwise</option></select>') +
                row('Roof', '<select data-k="turnroof" aria-label="Roof turn"><option value="auto">Auto</option><option value="0">Upright</option><option value="90">90° Clockwise</option><option value="180">Upside Down</option><option value="270">90° Counter-Clockwise</option></select>') +
            '</details>' +
            (existTop ? '' : existHtml) +
            '<div class="spb-nk-flat" hidden role="note">Flat file: numbers already painted into it stay under the new ones. Cover them with a base colour first.</div>' +      // [SPB-TICKETS-2 2026-10-10 IQ2-2]
            '<div class="spb-nk-sim" hidden>' + svg('alert') + '<div><b>Sim-Stamped Number is on.</b> iRacing stamps its own number on top of your paint, so this number will be covered. ' +
                '<button type="button" data-act="custom">Use Custom Number</button></div></div>' +
            '<div class="spb-nk-note" aria-live="polite"></div>' +
            '<div class="spb-nk-pb"><button type="button" data-act="remove" hidden>Remove Kit</button><span class="spb-nk-gap"></span>' +
                '<button type="button" data-act="recentre" title="Measure the car again and put every number back in its default place">' + svg('refresh', 12) + 'Re-Centre</button>' +
                '<button type="button" data-act="cancel">Cancel</button><button type="button" data-act="commit" class="spb-nk-primary">Add Number Kit</button></div>';
        doc.body.appendChild(panel);
        panel.addEventListener('input', onInput); panel.addEventListener('change', onInput);
        panel.addEventListener('click', onClick);
        panel.addEventListener('keydown', onKey);
        panel.addEventListener('pointerdown', onDragStart);
        return panel;
    }

    // ------------------------------------------------------------------ model <-> controls
    function readKit() {
        var g = function (k) { return panel.querySelector('[data-k="' + k + '"]'); }, v = function (k) { var e = g(k); return e ? e.value : undefined; }, c = function (k) { var e = g(k); return !!(e && e.checked); };
        var places = {}; panel.querySelectorAll('[data-place]').forEach(function (b) { places[b.getAttribute('data-place')] = b.getAttribute('aria-pressed') === 'true'; });
        return {
            number: v('number'), font: v('font'), bold: c('bold'), italic: c('italic'), slant: v('slant'), spacing: v('spacing'), fill: v('fill'),
            ring1: { color: v('ring1c'), w: v('ring1w') }, ring2: { color: v('ring2c'), w: v('ring2w') },
            shadow: { on: c('shon'), color: v('shc'), dist: v('shd'), soft: v('shs'), alpha: S ? S.kit.shadow.alpha : 85, angle: S ? S.kit.shadow.angle : 45 },
            plate: { on: c('plon'), shape: v('plshape'), color: v('plc'), border: v('plb'), bw: S ? S.kit.plate.bw : 2, pad: S ? S.kit.plate.pad : 16 },
            places: places, roofFrom: v('roofFrom'), size: v('size'), material: v('material'),
            turn: { left: v('turnleft'), right: v('turnright'), roof: v('turnroof') }
        };
    }
    function fillKit(k) {
        var set = function (key, val) { var e = panel.querySelector('[data-k="' + key + '"]'); if (!e) return; if (e.type === 'checkbox') e.checked = !!val; else e.value = String(val); };
        set('number', k.number); set('font', k.font); set('bold', k.bold); set('italic', k.italic); set('slant', k.slant); set('spacing', k.spacing); set('fill', k.fill);
        set('ring1c', k.ring1.color); set('ring1w', k.ring1.w); set('ring2c', k.ring2.color); set('ring2w', k.ring2.w);
        set('shon', k.shadow.on); set('shc', k.shadow.color); set('shd', k.shadow.dist); set('shs', k.shadow.soft);
        set('plon', k.plate.on); set('plshape', k.plate.shape); set('plc', k.plate.color); set('plb', k.plate.border);
        set('roofFrom', k.roofFrom); set('size', k.size); set('material', k.material);
        set('turnleft', k.turn.left); set('turnright', k.turn.right); set('turnroof', k.turn.roof);
        panel.querySelectorAll('[data-place]').forEach(function (b) { b.setAttribute('aria-pressed', k.places[b.getAttribute('data-place')] ? 'true' : 'false'); });
        var sv = panel.querySelector('[data-val="size"]'); if (sv) sv.textContent = Math.round(k.size) + '%';
    }
    function refreshAvail() {
        var geo = S && S.geo, has = geo && geo.ok;
        panel.querySelectorAll('[data-place]').forEach(function (b) {
            var p = b.getAttribute('data-place'), ok = has && !!geo.places[p];
            b.disabled = !ok; b.title = ok ? ('Number on the ' + core().PLACE_LABEL[p].toLowerCase()) : (has ? 'This car map has no ' + core().PLACE_LABEL[p].toLowerCase() + '.' : 'The car parts were not found on this paint.');
        });
        var M = root.SPBRevLayerMat, mrow = panel.querySelector('.spb-nk-matrow'); if (mrow) mrow.style.display = (M && !(M.off && M.off())) ? '' : 'none';
        var ro = panel.querySelector('[data-k="roofFrom"]'); if (ro) ro.disabled = !(has && geo.places.roof);
    }
    function updateThumb() {
        var cv = panel && panel.querySelector('.spb-nk-thumb'); if (!cv || !S) return;
        var g = cv.getContext('2d'); g.clearRect(0, 0, cv.width, cv.height);
        try {
            var r = core().render(S.kit, cv.width - 8, cv.height - 6, 0), im = r.canvas, s = Math.min((cv.width - 8) / im.width, (cv.height - 6) / im.height, 1);
            g.fillStyle = '#7a7a82'; g.fillRect(0, 0, cv.width, cv.height);
            g.drawImage(im, (cv.width - im.width * s) / 2, (cv.height - im.height * s) / 2, im.width * s, im.height * s);
        } catch (e) { warn('thumb', e); }
    }
    function updateNotes() {
        if (!panel || !S) return;
        var geo = S.geo, note = panel.querySelector('.spb-nk-note'), parts = [];
        if (!geo || !geo.ok) { note.textContent = (geo && geo.why ? geo.why + ' ' : '') + 'The number goes in the middle of the sheet; drag the layer into place.'; }
        else {
            var out = [];
            core().PLACES.forEach(function (p) {
                if (!S.kit.places[p] || !geo.places[p]) return; var at = S.at[p]; if (!at) return;
                out.push(core().PLACE_LABEL[p] + ' ' + (Math.round(at.theta * 180 / Math.PI + 360) % 360) + '°');
            });
            parts.push(out.length ? 'Turned on the car: ' + out.join(' · ') : 'Pick at least one place.');
            if (S.matched && Object.keys(S.matched).length) parts.push('Sized and placed like the numbers it replaces' + (S.slantAuto ? ' (slant ' + Math.round(S.effSlant) + '°)' : '') + '; Size 100% is their size.');
            core().PLACES.forEach(function (p) { if (S.kit.places[p] && geo.places[p]) (geo.places[p].notes || []).forEach(function (n) { if (parts.indexOf(n) < 0) parts.push(n); }); });
            note.textContent = parts.join(' ');
        }
        var ex = panel.querySelector('.spb-nk-exist');
        if (S.mode === 'new' && S.existingHits && S.existingHits.length) {
            var pl = []; S.existingHits.forEach(function (e) { e.hits.forEach(function (h) { var l = core().PLACE_LABEL[h.place]; if (pl.indexOf(l) < 0) pl.push(l); }); });
            ex.hidden = false; ex.querySelector('.spb-nk-exist-t').textContent = 'This car already has numbers on its Numbers layer (' + pl.join(', ') + ').';
            ex.querySelectorAll('[data-rep]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-rep') === S.replace ? 'true' : 'false'); });
        } else ex.hidden = true;
        var flat = panel.querySelector('.spb-nk-flat'); if (flat) flat.hidden = !(flatSource() && !t2Off('IQ22'));      // [SPB-TICKETS-2 2026-10-10 IQ2-2] before: nothing said the old numbers stay under the new ones on a flat TGA
        var sim = doc.getElementById('useSimStampedCheckbox'), sw = panel.querySelector('.spb-nk-sim'); if (sw) sw.hidden = !(sim && sim.checked);
        var add = panel.querySelector('[data-act="commit"]'), rm = panel.querySelector('[data-act="remove"]');
        if (add) { add.textContent = S.mode === 'edit' ? 'Done' : 'Add Number Kit'; add.disabled = !(S.liveIds && S.liveIds.length); }
        if (rm) rm.hidden = S.mode !== 'edit';
        panel.querySelector('.spb-nk-title').textContent = S.mode === 'edit' ? 'Number Kit: Editing' : 'Number Kit';
    }
    function refresh() {
        var sl = panel && panel.querySelector('[data-k="slant"]'); if (sl && S && doc.activeElement !== sl && S.effSlant != null) sl.value = String(S.effSlant);
        updateThumb(); updateNotes();
    }

    // ------------------------------------------------------------------ events
    function queue() {
        if (raf) return;
        raf = (root.requestAnimationFrame || function (f) { return setTimeout(f, 16); })(function () {
            raf = 0; if (!S) return;
            var k = readKit(); if (!/^[A-Za-z0-9]{1,4}$/.test(String(k.number || ''))) { panel.querySelector('[data-k="number"]').setAttribute('aria-invalid', 'true'); return; }
            panel.querySelector('[data-k="number"]').removeAttribute('aria-invalid');
            if (S.slantAuto) delete k.slant;            // while Replace Existing matches the old numbers' lean, the slant box shows that lean and is not read back
            S.set(k); S.kit = core().normalize(S.kit); saveLast(S.kit); refresh();
        });
    }
    function onInput(e) {
        var t = e.target; if (!t || !t.getAttribute) return; if (!t.getAttribute('data-k') && !t.getAttribute('data-place')) return;
        if (t.getAttribute('data-k') === 'slant' && S) S.slantAuto = false;     // the user typed a slant: it wins over the matched one
        if (t.getAttribute('data-k') === 'size') { var sv = panel.querySelector('[data-val="size"]'); if (sv) sv.textContent = Math.round(t.value) + '%'; }
        queue();
    }
    function onClick(e) {
        var chip = e.target.closest && e.target.closest('[data-place]');
        if (chip && !chip.disabled) { chip.setAttribute('aria-pressed', chip.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); queue(); return; }
        var rep = e.target.closest && e.target.closest('[data-rep]');
        if (rep && S) { S.setReplace(rep.getAttribute('data-rep')); S.existingHits && S.existingHits.forEach(function (x) { x.__key = null; }); S.apply(); refresh(); return; }
        var b = e.target.closest && e.target.closest('[data-act]'); if (!b) return; e.preventDefault();
        var a = b.getAttribute('data-act');
        if (a === 'commit') { if (S) S.commit(); }
        else if (a === 'cancel') { if (S) S.cancel(); else closeUi(); }
        else if (a === 'remove') { if (S) S.remove(); }
        else if (a === 'recentre') { if (S) { S.recentre(); refresh(); } }
        else if (a === 'custom') { var c = doc.getElementById('useCustomNumberCheckbox'); if (c && !c.checked) c.click(); updateNotes(); }
    }
    function onKey(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (S) S.cancel(); return; }
        if (e.key === 'Enter' && e.target && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'SELECT' && e.target.tagName !== 'SUMMARY') { e.preventDefault(); if (S) S.commit(); }
    }
    // Ctrl+Z / Ctrl+Y while the dialog is open: finish the kit first so the app's own undo acts on a whole, committed kit
    doc.addEventListener('keydown', function (e) {
        if (!S || !panel || panel.style.display === 'none') return;
        if (e.key === 'Escape' && !e.defaultPrevented && !(e.target && panel.contains(e.target))) { try { S.cancel(); } catch (x) { warn('esc', x); } return; }   // Esc anywhere takes the live numbers back off
        if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && !(e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && e.target.type !== 'range' && e.target.type !== 'checkbox' && e.target.type !== 'color')) { try { S.commit(); } catch (x) { warn('commit on undo', x); } }
    }, true);
    var drag = null;
    function onDragStart(e) {
        var h = e.target.closest && e.target.closest('[data-drag]'); if (!h || (e.target.closest && e.target.closest('button'))) return;
        var r = panel.getBoundingClientRect(); drag = { dx: e.clientX - r.left, dy: e.clientY - r.top };
        var mv = function (ev) { if (!drag) return; panel.style.left = Math.max(0, Math.min((root.innerWidth || 1200) - 80, ev.clientX - drag.dx)) + 'px'; panel.style.top = Math.max(0, Math.min((root.innerHeight || 800) - 40, ev.clientY - drag.dy)) + 'px'; };
        var up = function () { doc.removeEventListener('pointermove', mv); doc.removeEventListener('pointerup', up); if (drag) { posSave({ l: parseInt(panel.style.left, 10), t: parseInt(panel.style.top, 10) }); } drag = null; };
        doc.addEventListener('pointermove', mv); doc.addEventListener('pointerup', up);
    }
    function place() {
        var saved = posLoad(), vw = root.innerWidth || 1200, vh = root.innerHeight || 800, w = panel.offsetWidth || 340;
        var m = doc.getElementById('spbSymMenu') || doc.getElementById('spbNumMenu'), a = (m && m.isConnected && m.getBoundingClientRect()) || { left: 80, bottom: 96 };
        var left = saved && isFinite(saved.l) ? saved.l : a.left, top = saved && isFinite(saved.t) ? saved.t : a.bottom + 6;
        panel.style.left = Math.max(4, Math.min(vw - w - 4, left)) + 'px'; panel.style.top = Math.max(4, Math.min(vh - 120, top)) + 'px';
        panel.style.maxHeight = Math.max(240, vh - parseInt(panel.style.top, 10) - 8) + 'px';
    }

    function clamp() {                                // the window got smaller (or the dialog was dragged): keep the whole dialog on screen
        if (!panel || panel.style.display === 'none') return;
        var vw = root.innerWidth || 1200, vh = root.innerHeight || 800, w = panel.offsetWidth || 340;
        var l = parseInt(panel.style.left, 10), t = parseInt(panel.style.top, 10);
        panel.style.left = Math.max(4, Math.min(vw - w - 4, isFinite(l) ? l : 4)) + 'px';
        panel.style.top = Math.max(4, Math.min(vh - 120, isFinite(t) ? t : 4)) + 'px';
        panel.style.maxHeight = Math.max(240, vh - parseInt(panel.style.top, 10) - 8) + 'px';
    }
    root.addEventListener('resize', clamp);

    // ------------------------------------------------------------------ open / close
    function closeUi() { if (panel) panel.style.display = 'none'; S = null; }
    function selectedKitId() {
        try { var id = root._selectedLayerId, L = root._psdLayers; if (typeof _selectedLayerId !== 'undefined') id = _selectedLayerId; if (typeof _psdLayers !== 'undefined') L = _psdLayers;
            var l = (L || []).filter(function (x) { return x && x.id === id; })[0]; var p = l && core().kitOf(l); return p ? p.kid : null; } catch (e) { return null; }
    }
    function newestKitId() {                          // [SPB-TICKETS-FIX 2026-10-10 T-8] kid of the top-most Number Kit layer on the car (null = none)
        try { var ks = core().kitLayers(), best = null, bi = -1, L = (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers;
            ks.forEach(function (l) { var i = (L || []).indexOf(l); if (i > bi) { bi = i; best = core().kitOf(l); } });
            return best ? best.kid : null; } catch (e) { return null; }
    }
    function open(opts) {
        if (off()) return Promise.resolve(false);
        opts = opts || {};
        var T = root.SpbRevSymTools, wait = T && T.ensureBuilt ? T.ensureBuilt(false) : Promise.resolve(null);
        return Promise.resolve(wait).then(function () {
            var last = loadLast(), kid = opts.kid || selectedKitId();
            // [SPB-TICKETS-FIX 2026-10-10 T-8] (INTEGRATION-QA: after undoing back to kit 77 the dialog still showed the last typed 78 and
            // "Add Number Kit" would have added a second kit.) With no kit layer selected, open the car's own newest kit (edit mode = its
            // real values, "Done" / "Remove") instead of the last-typed values. Kill switch window.SPB_TFIX_OFF / SPB_TFIX_T8_OFF.
            if (!kid && !opts.kit && !root.SPB_TFIX_OFF && !root.SPB_TFIX_T8_OFF) kid = newestKitId();
            var kitIn = kid ? null : (opts.kit || last);
            var s = core().begin({ kid: kid, kit: kitIn });
            if (!s) return false;
            S = s; s.onClose = function () { closeUi(); };
            buildPanel(); fillKit(S.kit); panel.style.display = ''; place();
            S.measure();
            if (S.mode === 'new') S.scanExisting();
            refreshAvail();
            // a place that this car does not have cannot stay ticked
            var k = readKit(), geo = S.geo, fix = false;
            if (geo && geo.ok) core().PLACES.forEach(function (p) { if (k.places[p] && !geo.places[p]) { k.places[p] = false; fix = true; } });
            if (!(geo && geo.ok)) { /* free placement */ }
            if (S.mode === 'new' && geo && geo.ok && !core().PLACES.some(function (p) { return k.places[p]; })) { core().PLACES.forEach(function (p) { if (geo.places[p]) k.places[p] = true; }); fix = true; }
            if (fix) { S.kit = core().normalize(Object.assign({}, S.kit, k)); fillKit(S.kit); }
            S.apply(); refresh();
            var inp = panel.querySelector('[data-k="number"]'); if (inp) { try { inp.focus({ preventScroll: true }); inp.select(); } catch (e) {} }
            return true;
        });
    }

    // ------------------------------------------------------------------ entry points
    function addMenuItem() {
        if (off()) return false;
        var pop = doc.querySelector('#spbSymMenu .spb-tb-pop');
        if (!pop) return false;
        if (pop.querySelector('[data-nkit]')) return true;
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'vtool-btn'; b.setAttribute('data-nkit', 'open');
        b.title = 'Number Kit: type the car number once and get it on both doors and the roof, turned to read right on the car';
        b.innerHTML = '<span class="spb-mi-ico spb-sym-ico">' + svg('hash') + '</span> Number Kit…';
        var anchor = pop.querySelector('[data-sym="stripe"]');
        if (anchor && anchor.nextSibling) pop.insertBefore(b, anchor.nextSibling); else pop.appendChild(b);
        b.addEventListener('click', function (e) { e.preventDefault(); var m = pop.closest('details'); if (m) m.removeAttribute('open'); open(); });
        return true;
    }
    function addOwnMenu() {                           // Symmetry is off: a small menu of our own so the kit is still reachable
        if (off() || doc.getElementById('spbNumMenu') || doc.getElementById('spbSymMenu')) return false;
        var anchor = doc.getElementById('spbRevMatMenu') || doc.getElementById('spbRetouchMenu'); if (!anchor || !anchor.parentNode) return false;
        var m = doc.createElement('details'); m.className = 'spb-tb-menu'; m.id = 'spbNumMenu';
        m.innerHTML = '<summary class="spb-tb-summary" title="Number Kit: the car number on both doors and the roof">Numbers <span class="spb-tb-caret">▾</span></summary><div class="spb-tb-pop"><button type="button" class="vtool-btn" data-nkit="open"><span class="spb-mi-ico">' + svg('hash') + '</span> Number Kit…</button></div>';
        anchor.parentNode.insertBefore(m, anchor.nextSibling);
        m.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-nkit]'); if (b) { e.preventDefault(); m.removeAttribute('open'); open(); } });
        return true;
    }
    function hookTextTool() {
        var T = root.SPBTextEdit; if (!T || T.__nkHooked || typeof T.handleClick !== 'function') return !!(T && T.__nkHooked);
        var orig = T.handleClick;
        T.handleClick = function (x, y) {
            // [SPB-REV-NUMBERS 2026-10-10] a Text-tool click on a Number Kit number re-opens the kit (all places update together)
            try { if (!off() && !(S && panel && panel.style.display !== 'none')) { var l = core().hitKit(x, y); if (l) { var p = core().kitOf(l); open({ kid: p.kid }); return true; } } } catch (e) { warn('text hook', e); }
            return orig.apply(this, arguments);
        };
        T.__nkHooked = true; return true;
    }
    function boot(tries) {
        if (off()) { if ((tries || 0) < 120) setTimeout(function () { boot((tries || 0) + 1); }, 1000); return; }
        var m = addMenuItem(), t = hookTextTool();
        if (!m && (tries || 0) > 24) m = addOwnMenu();
        if ((!m || !t) && (tries || 0) < 80) setTimeout(function () { boot((tries || 0) + 1); }, 500);
        else if (m) setInterval(function () { if (!off()) addMenuItem(); }, 3000);     // the Symmetry menu can be rebuilt; keep our item in it
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { boot(0); }); else boot(0);

    root.SpbRevNumbersUI = { open: open, close: function () { if (S) S.cancel(); else closeUi(); }, isOpen: function () { return !!(S && panel && panel.style.display !== 'none'); }, panel: function () { return panel; }, session: function () { return S; } };
})(typeof window !== 'undefined' ? window : globalThis);
