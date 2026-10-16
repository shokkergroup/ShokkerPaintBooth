/* [SPB-REV-LAYERMAT 2026-10-10] Layer Materials UI: a material chip on the layer row + a Material row in the
 * selected layer's details, both opening one compact fixed-position picker (search, the presets, any SPB
 * finish through the app's OWN finish picker, Edge, Vinyl Edge Lip, Keep Art Colour).
 * Hooks: a lazy, idempotent wrap of window.renderLayerPanel (decorate after it draws) and of
 * window.selectSwatchItem (only while OUR browse button opened the picker). Nothing in the layout moves:
 * the picker is position:fixed. Kill switch: SPB_REV_LAYERMAT_OFF (see layermat-core.js).
 */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    const C = root.SPBRevLayerMat;
    if (!C) return;
    const TAG = '[REV-LAYERMAT]';
    const SVGNS = 'http://www.w3.org/2000/svg';

    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function toast(msg, warn) { try { if (typeof root.showToast === 'function') root.showToast(msg, warn ? 'warn' : undefined); } catch (_) {} }

    // ---------------------------------------------------------------- swatches (content, not icons) + the one line icon
    function swClass(ref) {
        if (!ref) return 'none';
        if (ref.preset) return ref.preset;
        return 'finish';
    }
    function finishSwatch(fid) {
        const raw = String(fid || '').replace(/^mono:/, '');
        try { if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[raw] && BASES_BY_ID[raw].swatch) return BASES_BY_ID[raw].swatch; } catch (_) {}
        try { if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[raw] && MONOLITHICS_BY_ID[raw].swatch) return MONOLITHICS_BY_ID[raw].swatch; } catch (_) {}
        return null;
    }
    function swatchEl(ref) {
        const i = doc.createElement('i');
        i.className = 'spb-lm-sw spb-lm-sw--' + swClass(ref);
        if (ref && !ref.preset && ref.finishId) { const c = finishSwatch(ref.finishId); if (c && /^#[0-9a-f]{3,8}$/i.test(c)) i.style.background = c; }
        if (!ref) i.appendChild(lineIcon());
        return i;
    }
    function lineIcon() {   // material sphere outline: a circle + a highlight arc (monochrome, currentColor)
        const s = doc.createElementNS(SVGNS, 'svg');
        s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('width', '12'); s.setAttribute('height', '12'); s.setAttribute('aria-hidden', 'true');
        const c = doc.createElementNS(SVGNS, 'circle'); c.setAttribute('cx', '8'); c.setAttribute('cy', '8'); c.setAttribute('r', '6');
        const p = doc.createElementNS(SVGNS, 'path'); p.setAttribute('d', 'M5 6.2a3.6 3.6 0 0 1 3.2-2');
        [c, p].forEach(function (n) { n.setAttribute('fill', 'none'); n.setAttribute('stroke', 'currentColor'); n.setAttribute('stroke-width', '1.4'); n.setAttribute('stroke-linecap', 'round'); s.appendChild(n); });
        return s;
    }

    // ---------------------------------------------------------------- layer panel decoration
    function targetsFor(id) {
        try {
            const sel = root._selectedLayerIds;
            if (sel && typeof sel.has === 'function' && sel.size > 1 && sel.has(id)) return Array.from(sel).map(String);
        } catch (_) {}
        return [String(id)];
    }
    function decorate() {
        if (C.off()) return;
        const panel = doc.getElementById('layerPanelContent');
        if (!panel) return;
        wirePanel(panel);
        const rows = panel.querySelectorAll('.layer-row[data-layer-id]');
        for (let k = 0; k < rows.length; k++) {
            const row = rows[k], id = row.getAttribute('data-layer-id');
            const L = C.byId(id);
            if (!L || C.isHelper(L)) continue;
            const rec = C.get(L), selected = row.classList.contains('selected');
            let chip = row.querySelector(':scope > .spb-lm-chip');
            if (!rec && !selected) { if (chip) chip.remove(); continue; }
            const label = 'Layer Material: ' + C.describe(rec) + ' — click to ' + (rec ? 'change' : 'assign');
            if (!chip || chip.getAttribute('data-lm-sig') !== JSON.stringify(rec)) {
                if (chip) chip.remove();
                chip = doc.createElement('button');
                chip.type = 'button';
                chip.className = 'spb-lm-chip' + (rec ? ' is-set' : '');
                chip.setAttribute('data-lm-id', id);
                chip.setAttribute('data-lm-sig', JSON.stringify(rec));
                chip.setAttribute('aria-label', label);
                chip.title = label;
                chip.appendChild(swatchEl(rec));
                const before = row.querySelector(':scope > .layer-alpha-lock-toggle, :scope > .layer-clipping-toggle, :scope > .layer-lock-toggle');
                if (before) row.insertBefore(chip, before); else row.appendChild(chip);
            }
            // the selected row's details: one Material row
            if (selected) {
                const det = row.nextElementSibling;
                if (det && det.classList.contains('layer-row-details') && !det.querySelector('[data-lm-row]')) det.appendChild(detailsRow(id, rec));
            }
        }
    }
    function detailsRow(id, rec) {
        const r = doc.createElement('div');
        r.className = 'spb-lm-row';
        r.setAttribute('data-lm-row', id);
        const lab = doc.createElement('span'); lab.className = 'spb-lm-row-lab'; lab.textContent = 'Material';
        const b = doc.createElement('button');
        b.type = 'button'; b.className = 'spb-lm-open'; b.setAttribute('data-lm-id', id);
        b.title = 'Layer Material: the spec map for this layer’s pixels follows the layer (move, scale, rotate, edit). Click to change.';
        b.appendChild(swatchEl(rec));
        const nm = doc.createElement('span'); nm.className = 'spb-lm-name'; nm.textContent = rec ? C.refName(rec) : 'None (zones decide)';
        b.appendChild(nm);
        const extra = [];
        if (rec && rec.keep) extra.push('Keep Colour');
        if (rec && rec.edge) extra.push(C.refName(rec.edge) + ' Edge ' + rec.edge.width + ' px');
        if (rec && rec.lip) extra.push('Lip');
        if (extra.length) { const x = doc.createElement('b'); x.textContent = extra.join(' · '); b.appendChild(x); }
        r.appendChild(lab); r.appendChild(b);
        return r;
    }
    let wiredPanel = null;
    function wirePanel(panel) {
        if (wiredPanel === panel) return;
        wiredPanel = panel;
        panel.addEventListener('click', function (ev) {
            const t = ev.target && ev.target.closest ? ev.target.closest('.spb-lm-chip, .spb-lm-open') : null;
            if (!t || !panel.contains(t)) return;
            ev.stopPropagation(); ev.preventDefault();
            openPop(t.getAttribute('data-lm-id'), t);
        }, true);
        panel.addEventListener('dblclick', function (ev) {
            if (ev.target && ev.target.closest && ev.target.closest('.spb-lm-chip, .spb-lm-open')) { ev.stopPropagation(); ev.preventDefault(); }
        }, true);
    }
    function wrapPanel() {
        const cur = root.renderLayerPanel;
        if (typeof cur !== 'function' || cur.__spbLayerMat) return;
        const w = function () {
            const r = cur.apply(this, arguments);
            try { if (!C.off()) { decorate(); C.noticeChange(false); if (pop && pop.style.display !== 'none') refreshPop(); } } catch (e) { console.warn(TAG, 'decorate', e); }
            return r;
        };
        w.__spbLayerMat = true;
        root.renderLayerPanel = w;
    }

    // ---------------------------------------------------------------- the picker
    let pop = null, popFor = null, popAnchor = null, query = '';
    function el(tag, cls, text) { const e = doc.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
    function ensurePop() {
        if (pop) return pop;
        pop = el('div', 'spb-lm-pop');
        pop.id = 'spbLmPop';
        pop.setAttribute('role', 'dialog');
        pop.setAttribute('aria-label', 'Layer Material');
        pop.style.display = 'none';
        doc.body.appendChild(pop);
        pop.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { ev.stopPropagation(); closePop(); } });
        doc.addEventListener('mousedown', function (ev) {
            if (!pop || pop.style.display === 'none') return;
            const t = ev.target;
            if (pop.contains(t)) return;
            // the app's own finish picker (and its hover popout / stage) belongs to "Browse All SPB Finishes": keep ours open
            if (t && t.closest && (t.closest('#swatchPopup, #swatchHoverPopout, [id^="swatch"], .swatch-item') || t.closest('.spb-lm-chip') || t.closest('.spb-lm-open'))) return;
            closePop();
        }, true);
        return pop;
    }
    function closePop() { if (pop) pop.style.display = 'none'; popFor = null; popAnchor = null; }
    function openPop(id, anchor) {
        if (C.off()) return;
        const L = C.byId(id);
        if (!L) return;
        if (pop && pop.style.display !== 'none' && popFor === String(id)) { closePop(); return; }
        ensurePop();
        popFor = String(id); popAnchor = anchor; query = '';
        refreshPop();
        pop.style.display = 'block';
        place();
        const s = pop.querySelector('.spb-lm-search');
        if (s) { try { s.focus({ preventScroll: true }); } catch (_) {} }
    }
    function place() {
        if (!pop || !popAnchor) return;
        const a = popAnchor.getBoundingClientRect();
        const vw = root.innerWidth, vh = root.innerHeight;
        const pw = pop.offsetWidth || 300, ph = pop.offsetHeight || 420;
        let x = a.left - pw - 10;                     // prefer the left of the layers panel (the art stays visible)
        if (x < 8) x = Math.min(vw - pw - 8, a.right + 10);
        let y = Math.min(Math.max(8, a.top - 20), vh - ph - 8);
        if (y < 8) y = 8;
        pop.style.left = Math.round(Math.max(8, x)) + 'px';
        pop.style.top = Math.round(y) + 'px';
    }
    function apply(rec, patch, label) {
        const ids = targetsFor(popFor);
        const r = C.assign(ids, rec, { patch: !!patch, label: label });
        if (r && r.ok && r.changed) toast((r.label || 'Layer Material') + ' — the spec follows the layer.');
        refreshPop();
        return r;
    }
    function presetButton(p, cur) {
        const b = el('button', 'spb-lm-item');
        b.type = 'button';
        const ref = p ? (p.kind === 'finish' ? { preset: p.id, finishId: p.finishId } : { preset: p.id }) : null;
        const on = p ? (cur && cur.preset === p.id) : !cur;
        if (on) b.classList.add('is-on');
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.appendChild(swatchEl(ref));
        b.appendChild(el('span', null, p ? p.name : 'None'));
        b.title = p ? (p.tip + (p.kind === 'spec' ? ' — M ' + p.m + ' · R ' + p.r + ' · CC ' + p.cc + ' (BASE_REGISTRY ' + p.src + ')' : '')) : 'No material: this layer’s spec comes from the zones, exactly as before';
        b.addEventListener('click', function () {
            if (!p) { apply(null, false, 'Layer Material: None'); return; }
            const cur2 = C.get(popFor);
            // keep the edge / lip settings when switching the main material
            apply(Object.assign({}, cur2 && cur2.edge ? { edge: cur2.edge } : {}, cur2 && cur2.lip ? { lip: cur2.lip } : {}, ref), false);
        });
        return b;
    }
    function finishCatalog() {
        const out = [];
        try { if (typeof BASES !== 'undefined' && Array.isArray(BASES)) BASES.forEach(function (b) { if (b && b.id && b.name) out.push({ id: b.id, name: b.name, swatch: b.swatch }); }); } catch (_) {}
        try { if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) MONOLITHICS.forEach(function (m) { if (m && m.id && m.name) out.push({ id: 'mono:' + m.id, name: m.name, swatch: m.swatch }); }); } catch (_) {}
        return out;
    }
    function refreshPop() {
        if (!pop || !popFor) return;
        const L = C.byId(popFor);
        if (!L) { closePop(); return; }
        const cur = C.get(L);
        const ids = targetsFor(popFor);
        const keepFocus = doc.activeElement && doc.activeElement.classList && doc.activeElement.classList.contains('spb-lm-search');
        pop.textContent = '';
        // header
        const hd = el('div', 'spb-lm-hd');
        hd.appendChild(el('span', 'spb-lm-title', 'Layer Material'));
        hd.appendChild(el('span', 'spb-lm-sub', ids.length > 1 ? ids.length + ' Layers' : (L.name || 'Layer')));
        const x = el('button', 'spb-lm-x', '×'); x.type = 'button'; x.setAttribute('aria-label', 'Close'); x.addEventListener('click', closePop);
        hd.appendChild(x);
        pop.appendChild(hd);
        // search
        const s = el('input', 'spb-lm-search');
        s.type = 'search'; s.placeholder = 'Search Materials And SPB Finishes'; s.value = query; s.setAttribute('aria-label', 'Search materials');
        s.addEventListener('input', function () { query = s.value; refreshList(); });
        pop.appendChild(s);
        const list = el('div', 'spb-lm-list');
        pop.appendChild(list);
        function refreshList() {
            list.textContent = '';
            const q = query.trim().toLowerCase();
            const presets = [null].concat(C.PRESETS).filter(function (p) { return !q || (p ? p.name : 'none').toLowerCase().indexOf(q) >= 0; });
            presets.forEach(function (p) { list.appendChild(presetButton(p, cur)); });
            if (cur && !cur.preset && cur.finishId && !q) {
                const b = el('button', 'spb-lm-item is-on'); b.type = 'button';
                b.appendChild(swatchEl({ finishId: cur.finishId })); b.appendChild(el('span', null, C.finishName(cur.finishId)));
                b.title = 'SPB finish (engine-rendered paint + spec)';
                list.appendChild(b);
            }
            if (q.length >= 2) {
                const hits = finishCatalog().filter(function (f) { return f.name.toLowerCase().indexOf(q) >= 0 || f.id.toLowerCase().indexOf(q) >= 0; }).slice(0, 8);
                hits.forEach(function (f) {
                    const b = el('button', 'spb-lm-item spb-lm-fin'); b.type = 'button';
                    if (cur && cur.finishId === f.id && !cur.preset) b.classList.add('is-on');
                    b.appendChild(swatchEl({ finishId: f.id })); b.appendChild(el('span', null, f.name));
                    b.title = 'SPB finish: ' + f.name + ' (engine-rendered paint + spec)';
                    b.addEventListener('click', function () {
                        const cur2 = C.get(popFor);
                        apply(Object.assign({}, cur2 && cur2.edge ? { edge: cur2.edge } : {}, cur2 && cur2.lip ? { lip: cur2.lip } : {}, { finishId: f.id }), false);
                    });
                    list.appendChild(b);
                });
                if (!hits.length && !presets.length) list.appendChild(el('div', 'spb-lm-empty', 'No match. Browse All SPB Finishes below.'));
            }
        }
        refreshList();
        const br = el('button', 'spb-lm-browse', 'Browse All SPB Finishes…');
        br.type = 'button'; br.id = 'spbLmBrowse';
        br.title = 'Open the app’s finish picker; the finish you pick becomes this layer’s material';
        br.addEventListener('click', function () { openAppPicker(br); });
        pop.appendChild(br);
        // options (only with a material)
        if (cur) {
            const opt = el('div', 'spb-lm-opts');
            if (C.refKind(cur) === 'finish') {
                opt.appendChild(check('Keep Art Colour', !!cur.keep, 'Use the finish for the spec map only and keep the layer’s own colours', function (on) { apply({ keep: on }, true, 'Layer Material: Keep Art Colour ' + (on ? 'On' : 'Off')); }));
            }
            // Edge
            const er = el('div', 'spb-lm-edge');
            er.appendChild(el('span', 'spb-lm-lab', 'Edge'));
            const sel = el('select', 'spb-lm-edge-mat'); sel.setAttribute('aria-label', 'Edge material');
            [{ v: '', n: 'None' }].concat(C.PRESETS.map(function (p) { return { v: p.id, n: p.name }; })).forEach(function (o) {
                const op = el('option', null, o.n); op.value = o.v; if ((cur.edge && cur.edge.preset === o.v) || (!cur.edge && !o.v)) op.selected = true; sel.appendChild(op);
            });
            if (cur.edge && !cur.edge.preset && cur.edge.finishId) { const op = el('option', null, C.finishName(cur.edge.finishId)); op.value = 'f:' + cur.edge.finishId; op.selected = true; sel.appendChild(op); }
            sel.addEventListener('change', function () {
                if (!sel.value) { apply({ edge: null }, true, 'Layer Material: Edge Off'); return; }
                const e0 = cur.edge || { width: 4, pos: 'inside' };
                const ref = sel.value.indexOf('f:') === 0 ? { finishId: sel.value.slice(2) } : { preset: sel.value };
                apply({ edge: Object.assign({ width: e0.width, pos: e0.pos }, ref) }, true, 'Layer Material: ' + C.refName(ref) + ' Edge');
            });
            er.appendChild(sel);
            const wIn = el('input', 'spb-lm-edge-w'); wIn.type = 'number'; wIn.min = '1'; wIn.max = String(C.EDGE_MAX); wIn.step = '1';
            wIn.value = String(cur.edge ? cur.edge.width : 4); wIn.disabled = !cur.edge; wIn.setAttribute('aria-label', 'Edge width in pixels'); wIn.title = 'Edge width (px)';
            wIn.addEventListener('change', function () { if (!cur.edge) return; apply({ edge: Object.assign({}, cur.edge, { width: Number(wIn.value) || 4 }) }, true, 'Layer Material: Edge Width'); });
            er.appendChild(wIn);
            er.appendChild(el('span', 'spb-lm-unit', 'px'));
            const seg = el('span', 'spb-lm-seg');
            ['inside', 'outside'].forEach(function (pos) {
                const b = el('button', null, pos === 'inside' ? 'Inside' : 'Outside'); b.type = 'button';
                const on = cur.edge && cur.edge.pos === pos; if (on) b.classList.add('is-on'); b.setAttribute('aria-pressed', on ? 'true' : 'false');
                b.disabled = !cur.edge;
                b.title = pos === 'inside' ? 'The edge band is the outer rim of the art' : 'The edge band wraps the art on the outside (an outline)';
                b.addEventListener('click', function () { if (cur.edge) apply({ edge: Object.assign({}, cur.edge, { pos: pos }) }, true, 'Layer Material: Edge ' + (pos === 'inside' ? 'Inside' : 'Outside')); });
                seg.appendChild(b);
            });
            er.appendChild(seg);
            opt.appendChild(er);
            opt.appendChild(check('Vinyl Edge Lip', !!cur.lip, 'A thin satin clearcoat lip along the decal edge (R ' + C.LIP.r + ' · CC ' + C.LIP.cc + ', BASE_REGISTRY satin)', function (on) { apply({ lip: on ? 60 : 0 }, true, 'Layer Material: Edge Lip ' + (on ? 'On' : 'Off')); }));
            pop.appendChild(opt);
        }
        // readout
        const ro = el('div', 'spb-lm-ro');
        if (!cur) ro.textContent = 'No material: the zones decide this layer’s spec.';
        else if (C.refKind(cur) === 'spec') { const p = C.PRESET_BY_ID[cur.preset]; ro.textContent = 'Spec M ' + p.m + ' · R ' + p.r + ' · CC ' + p.cc + ' from BASE_REGISTRY “' + p.src + '”. Paint unchanged.'; }
        else ro.textContent = 'SPB finish rendered by the engine (paint + spec)' + (cur.keep ? ', art colours kept.' : '.');
        pop.appendChild(ro);
        if (keepFocus) { try { s.focus({ preventScroll: true }); s.setSelectionRange(s.value.length, s.value.length); } catch (_) {} }
        place();
    }
    function check(label, on, tip, fn) {
        const w = el('label', 'spb-lm-check');
        const c = el('input'); c.type = 'checkbox'; c.checked = !!on;
        c.addEventListener('change', function () { fn(c.checked); });
        w.appendChild(c); w.appendChild(el('span', null, label)); w.title = tip;
        return w;
    }

    // ---------------------------------------------------------------- "Browse All SPB Finishes" = the app's own finish picker
    let browseBtn = null, browseFor = null, browseWatch = null;
    function browsing() {
        try { return !!(browseBtn && typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.open && swatchPopupState.triggerEl === browseBtn); } catch (_) { return false; }
    }
    function openAppPicker(btn) {
        if (typeof root.openSwatchPicker !== 'function') { toast('The finish picker is not available here.', true); return; }
        browseBtn = btn; browseFor = popFor;
        let zi = 0;
        try { zi = (typeof selectedZoneIndex === 'number' && zones[selectedZoneIndex]) ? selectedZoneIndex : 0; } catch (_) {}
        wrapPicker();
        root.openSwatchPicker(btn, 'base', zi);
        // the app's picker covers the screen: step aside while it is open, come back when it closes
        if (pop && browsing()) pop.style.visibility = 'hidden';
        if (browseWatch) clearInterval(browseWatch);
        browseWatch = setInterval(function () {
            if (browsing()) return;
            clearInterval(browseWatch); browseWatch = null;
            if (pop) { pop.style.visibility = ''; if (popFor && pop.style.display !== 'none') refreshPop(); }
        }, 250);
    }
    function wrapPicker() {
        const cur = root.selectSwatchItem;
        if (typeof cur !== 'function' || cur.__spbLayerMat) return;
        const w = function (id) {
            try {
                if (browsing() && (popFor || browseFor)) {
                    // the pick belongs to the LAYER the picker was opened for (never to the zone), even if our popover closed meanwhile
                    const keepFor = popFor;
                    popFor = popFor || browseFor;
                    if (id && id !== 'none' && id !== 'dualshift_custom') {
                        const cur2 = C.get(popFor);
                        apply(Object.assign({}, cur2 && cur2.edge ? { edge: cur2.edge } : {}, cur2 && cur2.lip ? { lip: cur2.lip } : {}, { finishId: String(id) }), false);
                    }
                    popFor = keepFor;
                    if (typeof root.closeSwatchPicker === 'function') root.closeSwatchPicker();
                    return;
                }
            } catch (e) { console.warn(TAG, 'picker', e); }
            return cur.apply(this, arguments);
        };
        w.__spbLayerMat = true;
        root.selectSwatchItem = w;
    }

    function init() {
        if (C.off()) return;
        wrapPanel();
        let n = 0;
        const t = setInterval(function () { wrapPanel(); if (++n > 40) clearInterval(t); }, 500);
        try { decorate(); } catch (_) {}
        root.addEventListener('resize', function () { if (pop && pop.style.display !== 'none') place(); });
    }
    root.SPBRevLayerMatUI = { open: openPop, close: closePop, decorate: decorate, refresh: refreshPop, isOpen: function () { return !!(pop && pop.style.display !== 'none'); }, forLayer: function () { return popFor; } };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
