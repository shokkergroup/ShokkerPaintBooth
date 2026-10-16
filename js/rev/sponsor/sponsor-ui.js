/* sponsor-ui.js - [SPB-REV-SPONSOR 2026-10-10] the Sponsor Kit dialog (js/rev/sponsor/sponsor-core.js does the work, sponsor-clean.js cleans the logo).
 * Entry point: Symmetry > Sponsor Kit...  (right under Number Kit). A fixed-position panel: nothing in the page layout moves when it opens, and opening it
 * changes nothing on the car until a logo is dropped. Every control re-places the layers live; Add Sponsor Kit commits them as ONE undo step;
 * Esc / Cancel takes them back off the car. Kill switch: window.SPB_REV_SPONSOR_OFF (see core).
 */
(function (root) {
    'use strict';
    var doc = root.document, TAG = '[SPB-REV-SPONSOR]';
    if (root.SpbRevSponsorUI) return;
    function core() { return root.SpbRevSponsor; }
    function CL() { return root.SpbRevSponsorClean; }
    function off() { return !core() || !CL() || core().off(); }
    function warn(w, e) { try { console.warn(TAG, w, e && e.message || e); } catch (_) {} }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k); } catch (_) {} }

    var ICON = {
        badge: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 10h6"/><path d="M7 14h10"/>',
        x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
        alert: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
        refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
        upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>'
    };
    function svg(k, sz) { return '<svg class="spb-sk-svg" viewBox="0 0 24 24" width="' + (sz || 14) + '" height="' + (sz || 14) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

    var panel = null, S = null, raf = 0, tmr = 0, LS = 'spb_rev_sponsor_last_v1';
    var R = null;                  // the logo as dropped: { canvas, name, kind } (kept while the dialog is open so Tolerance / Edge can be re-run)
    var CLEANED = null;            // last result of the clean: { canvas, info }
    var seq = 0;                   // newest clean wins
    function loadLast() { try { return JSON.parse(root.localStorage.getItem(LS) || 'null'); } catch (e) { return null; } }
    function saveLast(k) { try { root.localStorage.setItem(LS, JSON.stringify({ size: k.size, material: k.material, slots: k.slots, extraTurn: k.extraTurn })); } catch (e) {} }
    function posLoad() { try { return JSON.parse(root.localStorage.getItem(LS + '_pos') || 'null'); } catch (e) { return null; } }
    function posSave(p) { try { root.localStorage.setItem(LS + '_pos', JSON.stringify(p)); } catch (e) {} }

    // ------------------------------------------------------------------ panel
    var SHORT = { door_l: 'Left Door', door_r: 'Right Door', quarter_l: 'Left Quarter', quarter_r: 'Right Quarter', tv_l: 'Left TV', tv_r: 'Right TV', hood: 'Hood', deck: 'Trunk / Deck', rail_l: 'Left Rail', rail_r: 'Right Rail' };
    function row(label, inner, cls) { return '<div class="spb-sk-row' + (cls ? ' ' + cls : '') + '"><label>' + label + '</label>' + inner + '</div>'; }
    function buildPanel() {
        if (panel && panel.isConnected) return panel;
        var chips = core().SLOTS.map(function (s) {
            return '<button type="button" class="spb-sk-chip" data-slot="' + s.id + '" aria-pressed="false" title="' + esc(s.label) + '">' + esc(SHORT[s.id] || s.label) + '</button>';
        }).join('');
        var mats = core().MATERIALS.map(function (m) { return '<option value="' + m[0] + '">' + esc(m[1]) + '</option>'; }).join('');
        panel = doc.createElement('div'); panel.id = 'spbSponsorKit'; panel.className = 'spb-sk-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Sponsor Kit');
        panel.innerHTML =
            '<div class="spb-sk-ph" data-drag="1"><span class="spb-sk-pt">' + svg('badge') + '<span class="spb-sk-title">Sponsor Kit</span></span>' +
                '<button type="button" class="spb-sk-x" data-act="cancel" title="Close without adding (Esc)" aria-label="Close">' + svg('x', 12) + '</button></div>' +
            '<div class="spb-sk-drop" data-zone="1" tabindex="0" role="button" aria-label="Drop a logo here or press Enter to choose a file">' +
                '<div class="spb-sk-empty">' + svg('upload', 20) + '<div class="spb-sk-big">Drop a logo here</div><div class="spb-sk-small">PNG, JPG or SVG. A white box around it is fine.</div>' +
                    '<div class="spb-sk-btns"><button type="button" data-act="choose">Choose File…</button><button type="button" data-act="layer" title="Use the layer that is selected in the Layers panel">Use Selected Layer</button></div></div>' +
                '<div class="spb-sk-ba" hidden>' +
                    '<figure><canvas class="spb-sk-before" width="150" height="104" title="Click the background to pick its colour" aria-label="Logo before cleaning"></canvas><figcaption>Before <span class="spb-sk-hint">(click the box to pick it)</span></figcaption></figure>' +
                    '<figure><canvas class="spb-sk-after" width="150" height="104" aria-label="Logo after cleaning"></canvas><figcaption>After</figcaption></figure>' +
                '</div>' +
            '</div>' +
            '<input type="file" class="spb-sk-file" accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif,.svg,.png,.jpg,.jpeg" hidden>' +
            '<div class="spb-sk-clean" hidden>' +
                row('Clean', '<label class="spb-sk-chk" title="Take the white or flat box (and its JPEG fringe) off the logo"><input type="checkbox" data-k="cleanon">Remove Box</label>' +
                    '<label class="spb-sk-chk" title="Also clear boxed-in areas that match the box colour (the white inside letters)"><input type="checkbox" data-k="enclosed">Clear Inside</label>' +
                    '<button type="button" class="spb-sk-link" data-act="autobg" hidden title="Forget the picked colour and find the box automatically">Auto Colour</button>') +
                row('Tolerance', '<input type="range" data-k="tol" min="0" max="80" step="1" aria-label="Tolerance (0 is automatic)"><span class="spb-sk-val" data-val="tol"></span>') +
                row('Edge', '<input type="range" data-k="halo" min="0" max="4" step="1" aria-label="Edge cleanup (pixels pulled in)"><span class="spb-sk-val" data-val="halo"></span>') +
                '<div class="spb-sk-cnote" aria-live="polite"></div>' +
            '</div>' +
            row('Slots', '<div class="spb-sk-slots" role="group" aria-label="Slots">' + chips + '</div>', 'spb-sk-slotrow') +
            row('Size', '<input type="range" data-k="size" min="20" max="300" step="1" aria-label="Size"><span class="spb-sk-val" data-val="size"></span>') +
            '<div class="spb-sk-phys" aria-live="polite"></div>' +
            row('Material', '<select data-k="material" title="Spec material for the logo (Layer Materials)" aria-label="Material">' + mats + '</select>', 'spb-sk-matrow') +
            '<details class="spb-sk-adv"><summary>Sizes and Turns on This Car</summary><div class="spb-sk-sizes"></div>' +
                row('Extra Turn', '<select data-k="extraTurn" aria-label="Extra turn"><option value="0">None (reads right)</option><option value="90">90° Clockwise</option><option value="180">Upside Down</option><option value="270">90° Counter-Clockwise</option></select>') +
            '</details>' +
            '<div class="spb-sk-note" aria-live="polite"></div>' +
            '<div class="spb-sk-pb"><button type="button" data-act="remove" hidden>Remove Kit</button><span class="spb-sk-gap"></span>' +
                '<button type="button" data-act="recentre" title="Measure the car again and put every logo back in its default place">' + svg('refresh', 12) + 'Re-Centre</button>' +
                '<button type="button" data-act="cancel">Cancel</button><button type="button" data-act="commit" class="spb-sk-primary">Add Sponsor Kit</button></div>';
        doc.body.appendChild(panel);
        panel.addEventListener('input', onInput); panel.addEventListener('change', onInput);
        panel.addEventListener('click', onClick);
        panel.addEventListener('keydown', onKey);
        panel.addEventListener('pointerdown', onDragStart);
        panel.addEventListener('dragover', function (e) { if (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0) { e.preventDefault(); panel.classList.add('is-drop'); } });
        panel.addEventListener('dragleave', function (e) { if (!panel.contains(e.relatedTarget)) panel.classList.remove('is-drop'); });
        panel.addEventListener('drop', function (e) { panel.classList.remove('is-drop'); var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]; if (f) { e.preventDefault(); loadFile(f); } });
        panel.querySelector('.spb-sk-file').addEventListener('change', function (e) { var f = e.target.files && e.target.files[0]; if (f) loadFile(f); e.target.value = ''; });
        panel.querySelector('.spb-sk-before').addEventListener('click', onPickColour);
        return panel;
    }

    // ------------------------------------------------------------------ model <-> controls
    function g(k) { return panel.querySelector('[data-k="' + k + '"]'); }
    function readKit() {
        var slots = {}; panel.querySelectorAll('[data-slot]').forEach(function (b) { slots[b.getAttribute('data-slot')] = b.getAttribute('aria-pressed') === 'true'; });
        var cur = S ? S.kit.clean : {};
        return { size: g('size').value, material: g('material').value, extraTurn: g('extraTurn').value, slots: slots,
            clean: { on: g('cleanon').checked, enclosed: g('enclosed').checked, tol: g('tol').value, halo: g('halo').value, bg: cur.bg || null } };
    }
    function fillKit(k) {
        var set = function (key, val) { var e = g(key); if (!e) return; if (e.type === 'checkbox') e.checked = !!val; else e.value = String(val); };
        set('size', k.size); set('material', k.material); set('extraTurn', k.extraTurn);
        set('cleanon', k.clean.on); set('enclosed', k.clean.enclosed); set('tol', k.clean.tol); set('halo', k.clean.halo);
        panel.querySelectorAll('[data-slot]').forEach(function (b) { b.setAttribute('aria-pressed', k.slots[b.getAttribute('data-slot')] ? 'true' : 'false'); });
        vals();
    }
    function vals() {
        var t = g('tol'), h = g('halo'), s = g('size');
        panel.querySelector('[data-val="tol"]').textContent = +t.value === 0 ? 'Auto' : t.value;
        panel.querySelector('[data-val="halo"]').textContent = +h.value === 0 ? 'Off' : h.value + ' px';
        panel.querySelector('[data-val="size"]').textContent = Math.round(s.value) + '%';
    }
    function refreshAvail() {
        var geo = S && S.geo, has = geo && geo.ok;
        panel.querySelectorAll('[data-slot]').forEach(function (b) {
            var id = b.getAttribute('data-slot'), sl = core().SLOT_BY[id], ok = has && !!geo.slots[id];
            b.disabled = !ok;
            b.title = ok ? sl.label + (geo.slots[id].notes && geo.slots[id].notes.length ? ' (' + geo.slots[id].notes.join(' ') + ')' : '') : (has ? 'This car map has no ' + sl.label.toLowerCase() + '.' : 'The car parts were not found on this paint.');
        });
        var M = root.SPBRevLayerMat, mrow = panel.querySelector('.spb-sk-matrow'); if (mrow) mrow.style.display = (M && !(M.off && M.off())) ? '' : 'none';
    }

    // ------------------------------------------------------------------ before / after pictures
    function drawFit(cv, im, bgKind) {
        var g2 = cv.getContext('2d'), W = cv.width, H = cv.height; g2.clearRect(0, 0, W, H);
        if (bgKind === 'check') { for (var y = 0; y < H; y += 8) for (var x = 0; x < W; x += 8) { g2.fillStyle = ((x + y) / 8) % 2 ? '#4a4a52' : '#5c5c66'; g2.fillRect(x, y, 8, 8); } }
        else { g2.fillStyle = '#6e6e78'; g2.fillRect(0, 0, W, H); }
        if (!im) return; var s = Math.min((W - 6) / im.width, (H - 6) / im.height, 1.5);
        g2.imageSmoothingQuality = 'high'; g2.drawImage(im, (W - im.width * s) / 2, (H - im.height * s) / 2, im.width * s, im.height * s);
    }
    function drawBA() {
        var ba = panel.querySelector('.spb-sk-ba'), empty = panel.querySelector('.spb-sk-empty'), has = !!(S && S.logo && S.logo.canvas);
        ba.hidden = !has; empty.hidden = has; panel.querySelector('.spb-sk-drop').classList.toggle('has-logo', has);
        if (!has) return;
        drawFit(panel.querySelector('.spb-sk-before'), R ? R.canvas : S.logo.canvas, 'flat');
        drawFit(panel.querySelector('.spb-sk-after'), S.logo.canvas, 'check');
    }
    function cleanNote() {
        var el = panel.querySelector('.spb-sk-cnote'), box = panel.querySelector('.spb-sk-clean'); if (!S) return;
        var hasRaw = !!R; box.hidden = !hasRaw && !(S.logo && S.logo.canvas && S.mode === 'new');
        panel.querySelector('[data-act="autobg"]').hidden = !(S.kit.clean.bg);
        if (!hasRaw) {
            box.hidden = !(S.logo && S.logo.canvas); ['cleanon', 'enclosed', 'tol', 'halo'].forEach(function (k) { g(k).disabled = true; });
            el.textContent = S.logo && S.logo.cleaned ? 'This logo was cleaned when it was added; drop the original again to re-clean it.' : 'This logo is used as it is.'; el.className = 'spb-sk-cnote'; return;
        }
        ['cleanon', 'enclosed', 'tol', 'halo'].forEach(function (k) { g(k).disabled = false; });
        var i = CLEANED && CLEANED.info, msg = '', bad = false;
        if (!S.kit.clean.on) msg = 'Box removal is off: the logo is placed exactly as it was dropped.';
        else if (!i) msg = '';
        else if (i.mode === 'none') { msg = i.reason || 'No plain background was found.'; bad = true; }
        else if (i.mode === 'alpha') msg = 'Transparent logo: the white fringe on its edge was recoloured. ' + (i.specks ? i.specks + ' stray specks dropped.' : '');
        else msg = 'Box removed (' + (S.kit.clean.bg ? 'colour you picked' : 'found automatically') + ', tolerance ' + i.tol + '). ' + (i.specks ? i.specks + ' stray specks dropped. ' : '') + (i.enclosed ? i.enclosed + ' boxed-in pixels cleared.' : '');
        el.textContent = msg; el.className = 'spb-sk-cnote' + (bad ? ' is-bad' : '');
    }

    // ------------------------------------------------------------------ loading a logo + cleaning it
    function recompute() {
        if (!S || !R) return;
        var my = ++seq, k = S.kit.clean, res;
        try {
            if (k.on) res = CL().cleanCanvas(R.canvas, { tol: k.tol, halo: k.halo, enclosed: k.enclosed, bg: k.bg || undefined });
            else res = { canvas: R.canvas, info: { mode: 'off' } };
        } catch (e) { warn('clean', e); res = { canvas: R.canvas, info: { mode: 'none', reason: 'The clean step failed: ' + (e && e.message || e) } }; }
        if (my !== seq || !S) return;
        CLEANED = res;
        if (res.info.mode === 'none') {             // refuse to put a boxed logo on the car: show the problem, keep the car as it was
            S.clearLogo(); drawBA(); cleanNote(); updateAll(); return;
        }
        S.setLogo(res.canvas, { name: R.name, kind: R.kind, cleaned: !!k.on && res.info.mode !== 'off', info: res.info });
        drawBA(); cleanNote(); updateAll();
    }
    function useRaw(rec) {
        R = { canvas: rec.canvas, name: rec.name || 'Logo', kind: rec.kind || 'png' };
        if (S) { S.kit = core().normalize(Object.assign({}, S.kit, { clean: Object.assign({}, S.kit.clean, { bg: null, tol: 0 }), name: S.kit.name })); fillKit(S.kit); }
        recompute();
    }
    function loadFile(file) {
        if (!S) return Promise.resolve(false);
        var okType = /^image\/(png|jpe?g|svg\+xml|webp|gif)$/i.test(file.type || '') || /\.(png|jpe?g|svg|webp|gif)$/i.test(file.name || '');
        if (!okType) { note('That file is not a PNG, JPG or SVG picture.', true); return Promise.resolve(false); }
        return CL().decode(file).then(function (rec) { useRaw(rec); return true; }, function (e) { note((e && e.message) || 'That picture could not be opened.', true); return false; });
    }
    function loadCanvas(cv, name) { if (!S) return false; useRaw({ canvas: cv, name: name || 'Logo', kind: 'png' }); return true; }
    function useSelectedLayer() {
        var id, L; try { id = typeof _selectedLayerId !== 'undefined' ? _selectedLayerId : root._selectedLayerId; L = typeof _psdLayers !== 'undefined' ? _psdLayers : root._psdLayers; } catch (e) {}
        var l = (L || []).filter(function (x) { return x && x.id === id; })[0];
        if (!l) { note('Select a layer in the Layers panel first, then press Use Selected Layer.', true); return false; }
        if (core().isKitLayer(l)) { note('That layer already belongs to a Sponsor Kit. Pick another layer.', true); return false; }
        var rec = CL().fromLayer(l); if (!rec) { note('That layer is empty.', true); return false; }
        useRaw(rec); return true;
    }
    function onPickColour(e) {
        if (!S || !R) return; var cv = e.currentTarget, r = cv.getBoundingClientRect(); if (!r.width) return;
        var px = (e.clientX - r.left) / r.width * cv.width, py = (e.clientY - r.top) / r.height * cv.height;
        var sc = Math.min((cv.width - 6) / R.canvas.width, (cv.height - 6) / R.canvas.height, 1.5), ox = (cv.width - R.canvas.width * sc) / 2, oy = (cv.height - R.canvas.height * sc) / 2;
        var ix = Math.floor((px - ox) / sc), iy = Math.floor((py - oy) / sc); if (ix < 0 || iy < 0 || ix >= R.canvas.width || iy >= R.canvas.height) return;
        var d = R.canvas.getContext('2d', { willReadFrequently: true }).getImageData(ix, iy, 1, 1).data;
        var c = JSON.parse(JSON.stringify(S.kit.clean)); c.bg = [d[0], d[1], d[2]]; c.on = true; S.kit = core().normalize(Object.assign({}, S.kit, { clean: c })); fillKit(S.kit); recompute();
    }

    // ------------------------------------------------------------------ notes
    var noteMsg = '', noteBad = false;
    function note(msg, bad) { noteMsg = msg || ''; noteBad = !!bad; updateNotes(); }
    function f1(v) { return (Math.round(v * 10) / 10).toFixed(1); }
    function updateNotes() {
        if (!panel || !S) return;
        var geo = S.geo, el = panel.querySelector('.spb-sk-note'), phys = panel.querySelector('.spb-sk-phys'), sizes = panel.querySelector('.spb-sk-sizes'), rep = S.report();
        var hasLogo = !!(S.logo && S.logo.canvas);
        if (hasLogo) { var p = core().physical(S.kit, S.aspect()); phys.textContent = 'Same real size on every part: about ' + f1(p.wcm) + ' x ' + f1(p.hcm) + ' cm.'; } else phys.textContent = '';
        sizes.innerHTML = rep.length ? '<table class="spb-sk-tab"><tbody>' + rep.map(function (r) {
            var deg = Math.round(((r.theta * 180 / Math.PI) % 360 + 360) % 360);
            return '<tr><th>' + esc(SHORT[r.slot] || r.label) + '</th><td>' + f1(r.wcm) + ' x ' + f1(r.hcm) + ' cm</td><td>' + r.wpx + ' x ' + r.hpx + ' px</td><td>' + deg + '°</td></tr>';
        }).join('') + '</tbody></table>' : '<div class="spb-sk-none">No logo placed yet.</div>';
        var msg = [];
        if (noteMsg) msg.push(noteMsg);
        else if (!geo || !geo.ok) msg.push(((geo && geo.why) || '') + ' The logo goes in the middle of the sheet; drag the layer into place.');
        else if (!hasLogo) msg.push('Drop a logo, or use a layer that is already on the canvas. Nothing changes on the car until you do.');
        else {
            var picked = core().SLOTS.filter(function (s) { return S.kit.slots[s.id] && geo.slots[s.id]; });
            if (!picked.length) msg.push('Pick at least one slot.');
            else {
                msg.push('Turned to read right on the car. Drag any one layer to nudge it; Size moves them all.');
                // [SPB-TICKETS-2 2026-10-10 IQ2-1] a slot that had to step aside for a Number Kit number says so
                try { var _t2 = core().avoidSummary ? core().avoidSummary(rep) : ''; if (_t2) msg.push(_t2); } catch (e) { /* note only */ }
                var big = rep.filter(function (r) { return r.fit < 0.98; }).map(function (r) { return SHORT[r.slot]; });
                if (big.length) msg.push('Bigger than the room on: ' + big.join(', ') + ' (it will run over the edge there). Lower Size or untick the slot.');
            }
        }
        el.textContent = msg.join(' '); el.className = 'spb-sk-note' + (noteBad ? ' is-bad' : '');
        var add = panel.querySelector('[data-act="commit"]'), rm = panel.querySelector('[data-act="remove"]');
        if (add) { add.textContent = S.mode === 'edit' ? 'Done' : 'Add Sponsor Kit'; add.disabled = !(S.liveIds && S.liveIds.length); }
        if (rm) rm.hidden = S.mode !== 'edit';
        panel.querySelector('.spb-sk-title').textContent = S.mode === 'edit' ? 'Sponsor Kit: Editing' : 'Sponsor Kit';
    }
    function updateAll() { vals(); updateNotes(); }

    // ------------------------------------------------------------------ events
    var CLEAN_KEYS = { cleanon: 1, enclosed: 1, tol: 1, halo: 1 };
    function queue(cleanToo) {
        if (cleanToo) queue.dirty = true;
        if (raf) return;
        raf = (root.requestAnimationFrame || function (f) { return setTimeout(f, 16); })(function () {
            raf = 0; if (!S) return;
            var k = readKit(), prevClean = JSON.stringify(S.kit.clean); S.kit = core().normalize(Object.assign({}, S.kit, k, { clean: Object.assign({}, S.kit.clean, k.clean) }));
            saveLast(S.kit);
            if (queue.dirty && R && JSON.stringify(S.kit.clean) !== prevClean) { queue.dirty = false; clearTimeout(tmr); tmr = setTimeout(recompute, 40); }
            else { queue.dirty = false; S.set(S.kit); }
            updateAll();
        });
    }
    function onInput(e) {
        var t = e.target; if (!t || !t.getAttribute) return;
        var k = t.getAttribute('data-k'); if (!k && !t.getAttribute('data-slot')) return;
        vals(); queue(!!CLEAN_KEYS[k]);
    }
    function onClick(e) {
        var chip = e.target.closest && e.target.closest('[data-slot]');
        if (chip && !chip.disabled) { chip.setAttribute('aria-pressed', chip.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); queue(false); return; }
        var zone = e.target.closest && e.target.closest('[data-zone]');
        var b = e.target.closest && e.target.closest('[data-act]');
        if (!b) { if (zone && !(S && S.logo && S.logo.canvas) && !(e.target.closest && e.target.closest('button'))) panel.querySelector('.spb-sk-file').click(); return; }
        e.preventDefault();
        var a = b.getAttribute('data-act');
        if (a === 'commit') { if (S) S.commit(); }
        else if (a === 'cancel') { if (S) S.cancel(); else closeUi(); }
        else if (a === 'remove') { if (S) S.remove(); }
        else if (a === 'recentre') { if (S) { S.recentre(); updateAll(); } }
        else if (a === 'choose') { panel.querySelector('.spb-sk-file').click(); }
        else if (a === 'layer') { useSelectedLayer(); }
        else if (a === 'autobg') { if (S) { var c = JSON.parse(JSON.stringify(S.kit.clean)); c.bg = null; S.kit = core().normalize(Object.assign({}, S.kit, { clean: c })); fillKit(S.kit); recompute(); } }
    }
    function onKey(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (S) S.cancel(); return; }
        if (e.key === 'Enter' && e.target && e.target.getAttribute && e.target.getAttribute('data-zone')) { e.preventDefault(); panel.querySelector('.spb-sk-file').click(); return; }
        if (e.key === 'Enter' && e.target && !/^(BUTTON|SELECT|SUMMARY)$/.test(e.target.tagName) && !(e.target.getAttribute && e.target.getAttribute('data-zone'))) { e.preventDefault(); if (S && S.liveIds && S.liveIds.length) S.commit(); }
    }
    // Ctrl+Z / Ctrl+Y while the dialog is open: finish the kit first so the app's own undo acts on a whole, committed kit
    doc.addEventListener('keydown', function (e) {
        if (!S || !panel || panel.style.display === 'none') return;
        if (e.key === 'Escape' && !e.defaultPrevented && !(e.target && panel.contains(e.target))) { try { S.cancel(); } catch (x) { warn('esc', x); } return; }
        if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key) && !(e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && e.target.type !== 'range' && e.target.type !== 'checkbox' && e.target.type !== 'color')) { try { if (S.liveIds && S.liveIds.length) S.commit(); else S.cancel(); } catch (x) { warn('commit on undo', x); } }
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
        var saved = posLoad(), vw = root.innerWidth || 1200, vh = root.innerHeight || 800, w = panel.offsetWidth || 352;
        var m = doc.getElementById('spbSymMenu') || doc.getElementById('spbNumMenu'), a = (m && m.isConnected && m.getBoundingClientRect()) || { left: 80, bottom: 96 };
        var left = saved && isFinite(saved.l) ? saved.l : a.left, top = saved && isFinite(saved.t) ? saved.t : a.bottom + 6;
        panel.style.left = Math.max(4, Math.min(vw - w - 4, left)) + 'px'; panel.style.top = Math.max(4, Math.min(vh - 120, top)) + 'px';
        panel.style.maxHeight = Math.max(240, vh - parseInt(panel.style.top, 10) - 8) + 'px';
    }
    function clamp() {
        if (!panel || panel.style.display === 'none') return;
        var vw = root.innerWidth || 1200, vh = root.innerHeight || 800, w = panel.offsetWidth || 352;
        var l = parseInt(panel.style.left, 10), t = parseInt(panel.style.top, 10);
        panel.style.left = Math.max(4, Math.min(vw - w - 4, isFinite(l) ? l : 4)) + 'px';
        panel.style.top = Math.max(4, Math.min(vh - 120, isFinite(t) ? t : 4)) + 'px';
        panel.style.maxHeight = Math.max(240, vh - parseInt(panel.style.top, 10) - 8) + 'px';
    }
    root.addEventListener('resize', clamp);

    // ------------------------------------------------------------------ open / close
    function closeUi() { if (panel) panel.style.display = 'none'; S = null; R = null; CLEANED = null; noteMsg = ''; noteBad = false; }
    function selectedKitId() {
        try { var id = root._selectedLayerId, L = root._psdLayers; if (typeof _selectedLayerId !== 'undefined') id = _selectedLayerId; if (typeof _psdLayers !== 'undefined') L = _psdLayers;
            var l = (L || []).filter(function (x) { return x && x.id === id; })[0]; var p = l && core().kitOf(l); return p ? p.kid : null; } catch (e) { return null; }
    }
    function open(opts) {
        if (off()) return Promise.resolve(false);
        opts = opts || {};
        var T = root.SpbRevSymTools, wait = T && T.ensureBuilt ? T.ensureBuilt(false) : Promise.resolve(null);
        return Promise.resolve(wait).then(function () {
            var kid = opts.kid || selectedKitId(), rec = kid ? core().logoOf(kid) : null;
            return rec && rec.ready ? rec.ready.then(function () { return kid; }) : kid;
        }).then(function (kid) {
            var last = loadLast(), s = core().begin({ kid: kid, kit: kid ? null : Object.assign({}, last || {}, opts.kit || {}) });
            if (!s) return false;
            S = s; R = null; CLEANED = null; noteMsg = ''; noteBad = false; s.onClose = function () { closeUi(); };
            buildPanel(); fillKit(S.kit); panel.style.display = ''; place();
            S.measure(); refreshAvail();
            // a slot that this car does not have cannot stay ticked
            var k = readKit(), geo = S.geo, fix = false;
            if (geo && geo.ok) core().SLOTS.forEach(function (sl) { if (k.slots[sl.id] && !geo.slots[sl.id]) { k.slots[sl.id] = false; fix = true; } });
            if (S.mode === 'new' && geo && geo.ok && !core().SLOTS.some(function (sl) { return k.slots[sl.id]; })) { ['door_l', 'door_r', 'hood'].forEach(function (id) { if (geo.slots[id]) k.slots[id] = true; }); fix = true; }
            if (fix) { S.kit = core().normalize(Object.assign({}, S.kit, { slots: k.slots })); fillKit(S.kit); }
            if (S.mode === 'edit' && S.logo && S.logo.canvas) { S.apply(); }          // an edited kit re-places its layers (Size / slots) exactly where they are
            drawBA(); cleanNote(); updateAll();
            try { var z = panel.querySelector('.spb-sk-drop'); z.focus({ preventScroll: true }); } catch (e) {}
            return true;
        });
    }

    // ------------------------------------------------------------------ entry points
    function popOf() { return doc.querySelector('#spbSymMenu .spb-tb-pop') || doc.querySelector('#spbNumMenu .spb-tb-pop'); }
    function addMenuItem() {
        if (off()) return false;
        var pop = popOf(); if (!pop) return false;
        if (pop.querySelector('[data-skit]')) return true;
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'vtool-btn'; b.setAttribute('data-skit', 'open');
        b.title = 'Sponsor Kit: drop a logo, clean off its box, and put it on the doors, quarters, hood and more, turned to read right and the same real size everywhere';
        b.innerHTML = '<span class="spb-mi-ico spb-sym-ico">' + svg('badge') + '</span> Sponsor Kit…';
        var anchor = pop.querySelector('[data-nkit]') || pop.querySelector('[data-sym="stripe"]');
        if (anchor && anchor.nextSibling) pop.insertBefore(b, anchor.nextSibling); else pop.appendChild(b);
        b.addEventListener('click', function (e) { e.preventDefault(); var m = pop.closest('details'); if (m) m.removeAttribute('open'); open(); });
        return true;
    }
    function addOwnMenu() {
        if (off() || doc.getElementById('spbSponsorMenu') || doc.getElementById('spbSymMenu') || doc.getElementById('spbNumMenu')) return false;
        var anchor = doc.getElementById('spbRevMatMenu') || doc.getElementById('spbRetouchMenu'); if (!anchor || !anchor.parentNode) return false;
        var m = doc.createElement('details'); m.className = 'spb-tb-menu'; m.id = 'spbSponsorMenu';
        m.innerHTML = '<summary class="spb-tb-summary" title="Sponsor Kit: one logo on every part you pick">Sponsors <span class="spb-tb-caret">▾</span></summary><div class="spb-tb-pop"><button type="button" class="vtool-btn" data-skit="open"><span class="spb-mi-ico">' + svg('badge') + '</span> Sponsor Kit…</button></div>';
        anchor.parentNode.insertBefore(m, anchor.nextSibling);
        m.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-skit]'); if (b) { e.preventDefault(); m.removeAttribute('open'); open(); } });
        return true;
    }
    function boot(tries) {
        if (off()) { if ((tries || 0) < 120) setTimeout(function () { boot((tries || 0) + 1); }, 1000); return; }
        var m = addMenuItem();
        if (!m && (tries || 0) > 24) m = addOwnMenu();
        if (!m && (tries || 0) < 80) setTimeout(function () { boot((tries || 0) + 1); }, 500);
        else if (m) setInterval(function () { if (!off()) addMenuItem(); }, 3000);     // the Symmetry menu can be rebuilt; keep our item in it
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { boot(0); }); else boot(0);

    root.SpbRevSponsorUI = {
        open: open, close: function () { if (S) S.cancel(); else closeUi(); }, isOpen: function () { return !!(S && panel && panel.style.display !== 'none'); },
        panel: function () { return panel; }, session: function () { return S; }, loadFile: loadFile, loadCanvas: loadCanvas, useSelectedLayer: useSelectedLayer,
        raw: function () { return R; }, cleaned: function () { return CLEANED; }
    };
})(typeof window !== 'undefined' ? window : globalThis);
