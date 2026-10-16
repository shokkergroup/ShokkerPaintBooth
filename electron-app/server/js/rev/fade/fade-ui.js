/* [SPB-REV-FADE 2026-10-10] Car-Space Fade - the panel, the on-canvas preview, the undo trail and the render payload.
 *
 * Symmetry menu > "Car-Space Fade...": pick a direction (Nose -> Tail, Bottom -> Top, Centre -> Out, or two clicks on the car), two or more stops
 * (a colour and / or a material at each: Chrome, Matte, Satin, ... or any SPB finish) and the parts to fill. The fade runs in CAR space (js/rev/fade/
 * fade-space.js), so the left and right sides match at the same car position and hood -> roof -> trunk continue across the seams.
 *
 *  - While the panel is open the fade is drawn over the flat sheet (overlay canvas #spbRevFadeOverlay, downscaled while a direction / stop is being
 *    dragged, full resolution when you let go).
 *  - "Add Fade" stores a FADE RECORD (direction, parts, stops; the selection / zone clip at that moment). Records stay editable: reopen the panel and
 *    use Edit / Remove. Ctrl+Z / Ctrl+Y walk them through the app's own undo trail (SPBUndoExt kind 'rev-fade').
 *  - Live Preview and RENDER get the records inside the `_spb_rev_material` payload as a `fade` list (the same optional zone field the Material
 *    Brush uses), evaluated by engine/rev_fade_layer.py: so what is rendered is exactly what the preview shows. Finish stops build their zone with
 *    the Material Brush's own coat-zone helper and are rendered by the real engine.
 *
 * KILL SWITCH: window.SPB_REV_FADE_OFF = true or localStorage SPB_REV_FADE_OFF = '1': no menu entry, no payload, nothing changes.
 */
(function (root) {
    'use strict';
    const doc = root.document;
    if (!doc) return;
    const VER = 'fadeui1.0', KIND = 'rev-fade', UNDO_MAX = 40;
    const RF = () => root.SpbRevFade || null;
    const MAT = () => root.SPBRevMaterial || null;
    function off() { const r = RF(); return !r || r.off(); }
    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (e) {} }
    function warn(where, e) { if (root.console) root.console.warn('[REV-FADE] ' + where, e); }
    function fg() { try { return (typeof _foregroundColor !== 'undefined') ? _foregroundColor : (root._foregroundColor || '#d4202a'); } catch (e) { return '#d4202a'; } }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

    // ---------------------------------------------------------------- colours / materials
    function hex6(c) { const s = String(c || '').trim(); if (/^#[0-9a-f]{6}$/i.test(s)) return s.toLowerCase(); if (/^#[0-9a-f]{3}$/i.test(s)) return ('#' + s[1] + s[1] + s[2] + s[2] + s[3] + s[3]).toLowerCase(); return '#d4202a'; }
    function rgbOf(h) { h = hex6(h); return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
    function hexOf(a) { return '#' + a.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join(''); }
    function presets() { const R = root.SPBRevMatRecipes; return R && R.PRESETS ? R.PRESETS.filter(p => p.id !== 'raw') : []; }
    function specOfMat(id) { const p = presets().find(x => x.id === id); return p ? [p.m, p.r, p.cc] : null; }
    function finName(id) { const M = MAT(); try { return M && M.finishName ? M.finishName(id) : String(id); } catch (e) { return String(id); } }
    const DIRS = { nose: 'Nose → Tail', height: 'Bottom → Top', out: 'Centre → Out', custom: 'Custom' };
    const DIR_TIPS = {
        nose: 'Starts at the nose and ends at the tail. Both sides, the hood, roof and trunk all agree where "halfway" is.',
        height: 'Starts at the sills and ends at the roof. Side panels, roof and hood stay in step.',
        out: 'Starts on the centre line (hood, roof, trunk) and ends at the sills and bumper edges.',
        custom: 'Click the point where the fade starts, then the point where it ends. Drag the dots to adjust.'
    };

    // ---------------------------------------------------------------- state
    const S = { recs: [], undo: [], redo: [], seq: 0, gen: 0, listeners: [] };
    const ENC = new WeakMap();
    let D = null;                 // the draft being edited in the panel
    let panel = null, overlay = null, ro = null, into = null, tmpCv = null, raf = 0, reqStride = 1, settleT = 0, menuBtn = null;
    let pick = 0, dragH = -1, finTarget = -1, spaceBusy = false;
    function emit(what) { S.listeners.forEach(f => { try { f(what); } catch (e) {} }); }
    function cloneStop(s) { return { p: s.p, color: s.color, mat: s.mat, finish: s.finish }; }
    function cloneDir(d) { return { kind: d.kind, rev: !!d.rev, span: d.span || 'car', custom: d.custom ? Object.assign({}, d.custom, { p1: d.custom.p1 && d.custom.p1.slice(), p2: d.custom.p2 && d.custom.p2.slice() }) : null }; }
    function cloneRec(r) { return { id: r.id, key: r.key, name: r.name, dir: cloneDir(r.dir), parts: r.parts ? r.parts.slice() : null, paintOn: !!r.paintOn, keepDecals: r.keepDecals !== false, stops: r.stops.map(cloneStop), clip: r.clip || null }; }
    function lum(h) { const c = rgbOf(h); return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255; }
    function newDraft() {
        const f = hex6(fg()), a = lum(f) < 0.1 ? '#e8362d' : f, b = lum(a) > 0.45 ? '#14141a' : '#f4f4f6';   // a near-black foreground would give a fade you cannot see
        return { id: null, key: null, name: '', dir: { kind: 'nose', rev: false, span: 'car', custom: null }, parts: null, paintOn: true, keepDecals: true, clip: null,
            stops: [{ p: 0, color: a, mat: 'keep', finish: null }, { p: 1, color: b, mat: 'keep', finish: null }] };
    }
    function partsOf(rec, sp) { const all = sp.order; if (!rec.parts || !rec.parts.length) return all; const a = rec.parts.filter(n => sp.parts[n]); return a.length ? a : all; }
    function sortedStops(rec) { return rec.stops.slice().sort((a, b) => a.p - b.p); }
    function autoName(rec) { return DIRS[rec.dir.kind] + (rec.dir.rev ? ' (reversed)' : '') + (rec.dir.span === 'sel' ? ' · chosen parts' : ''); }
    function hasFinish(rec) { return rec.stops.some(s => s.mat === 'finish' && s.finish); }
    function describe(rec) {
        const st = sortedStops(rec);
        const bits = [];
        if (rec.paintOn) bits.push(st.length + ' colours');
        const mats = st.filter(s => s.mat !== 'keep').map(s => s.mat === 'finish' ? finName(s.finish || '') : (presets().find(p => p.id === s.mat) || {}).name).filter(Boolean);
        if (mats.length) bits.push(mats.join(' → '));
        return bits.join(' · ');
    }

    // ---------------------------------------------------------------- preview stops (JS mirror) + payload stops (engine)
    function previewStops(rec) {
        return sortedStops(rec).map(s => {
            const o = { p: Math.max(0, Math.min(1, s.p)), color: null, spec: null };
            if (rec.paintOn) o.color = rgbOf(s.color);
            if (s.mat !== 'keep' && s.mat !== 'finish') o.spec = specOfMat(s.mat);
            return o;
        });
    }

    // ---------------------------------------------------------------- overlay (on-canvas preview)
    function ensureOverlay() {
        const pc = doc.getElementById('paintCanvas'); if (!pc || !pc.parentNode) return null;
        if (!overlay) { overlay = doc.createElement('canvas'); overlay.id = 'spbRevFadeOverlay'; overlay.className = 'spb-fd-overlay'; overlay.setAttribute('aria-hidden', 'true'); wireOverlay(); }
        if (overlay.parentNode !== pc.parentNode) pc.parentNode.insertBefore(overlay, pc.nextSibling);
        if (!ro && root.ResizeObserver) { ro = new ResizeObserver(syncOverlay); ro.observe(pc); }
        syncOverlay(); return overlay;
    }
    function syncOverlay() {
        const pc = doc.getElementById('paintCanvas'); if (!overlay || !pc) return;
        if (overlay.width !== pc.width) overlay.width = pc.width;
        if (overlay.height !== pc.height) overlay.height = pc.height;
        overlay.style.left = pc.offsetLeft + 'px'; overlay.style.top = pc.offsetTop + 'px';
        overlay.style.width = pc.offsetWidth + 'px'; overlay.style.height = pc.offsetHeight + 'px';
    }
    // [SPB-REV-FADE 2026-10-10] The same clip the brushes use (active selection, else the selected zone's "Clip to" area) but sized from THE SHEET, not from the
    // Material Brush state: SPBRevMaterial.clipMask() reads its own S.W/S.H, which stay 0 until a Material tool has been used, and then hands back an EMPTY
    // mask (length 0 === 0*0) - a fade added before touching any material tool would then cover nothing. Found by t_gates1 (zone-clip gate), fixed here.
    function liveClip() {
        const r = RF(), sp = r && r.cur(); if (!sp) return null;
        const W = sp.W, H = sp.H;
        try { if (typeof _activeSelectionMask === 'function') { const m = _activeSelectionMask(W, H, true); if (m && m.length === W * H) return m; } } catch (e) { }
        try {
            const zc = window.SPBZoneClip;
            if (zc && !window.SPB_ZONECLIP_OFF && typeof zones !== 'undefined') { const z = zones[selectedZoneIndex]; if (z && zc.enabledFor(z)) { const m = zc.clipFor(z, W, H); if (m && m.length === W * H) return m; } }
        } catch (e) { }
        return null;
    }
    // [SPB-REV-FADE 2026-10-10 FADE-2] KEEP DECALS (owner doctrine: numbers, sponsors and logos are stamped ON TOP of the paint, and a tool must never erase them).
    // The fade is an engine post-pass, so it cannot be a layer "under" the decals the way REV-SYM-2's Car Stripe is; the equivalent is to take the decal layers'
    // footprint OUT of the fade's coverage (preview AND payload), so those pixels keep paint and spec exactly as they were. Which layers: the same rule as
    // REV-SYM-2 stripeInsertIndex (SpbProCar.roleOf = numbers | sponsors | decals / logos, with its name fallback) plus the visible "Car Mandatory" layer.
    // The footprint is the app's own ownership mask (getLayerVisibleContributionMask, alpha >= 50%), cached per layer-stack revision. A one-pixel ring around
    // it gets half the fade, so a decal's anti-aliased edge keeps most of its own colour instead of a hard halo. Per fade: "Keep decals" (default ON).
    // Kill switch for the whole behaviour: window.SPB_REV_FADE_DECALS_OFF = true.
    const ELEMENT_ROLES = /^(numbers|sponsors|decals \/ logos)$/;
    function layerRole(l) {
        let r = ''; try { if (root.SpbProCar && root.SpbProCar.roleOf) r = String(root.SpbProCar.roleOf(l) || ''); } catch (e) { }
        if (r && r !== 'other art') return r;
        const n = String(l.name || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
        if (/number/.test(n)) return 'numbers'; if (/sponsor/.test(n)) return 'sponsors';
        if (/logo|decal|banner|pitbox|windshield|sticker|badge/.test(n)) return 'decals / logos';
        if (/(^| )(base|body|livery|paint)( |$)|car paint|base (coat|layer|colou?r)/.test(n)) return 'body paint';
        return r || 'other art';
    }
    function isElementLayer(l) {
        if (!l || !l.img || l.visible === false) return false;
        if (/^\s*car mandatory\s*$/i.test(String(l.name || ''))) return true;
        return ELEMENT_ROLES.test(layerRole(l));
    }
    let DMC = null, DMSEQ = 0;   // { id, rev, W, H, sig, m } - the last decal mask
    function decalsOff() { return !!root.SPB_REV_FADE_DECALS_OFF; }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; } catch (e) { return root._psdLayers; } }
    function layerRev() { try { return (typeof _layerCompositeRevision !== 'undefined') ? _layerCompositeRevision : 0; } catch (e) { return 0; } }
    // Uint8Array(W*H): 0 inside a decal, 128 on the ring around it, 255 elsewhere - or null when the car has no decal layers.
    function decalMask(sp) {
        if (decalsOff() || !sp) return null;
        const fn = root.getLayerVisibleContributionMask, L = psdLayers();
        if (typeof fn !== 'function' || !Array.isArray(L) || !L.length) return null;
        const W = sp.W, H = sp.H, rev = layerRev();
        const els = L.filter(isElementLayer), sig = els.map(l => l.id).join(',');
        if (DMC && DMC.rev === rev && DMC.W === W && DMC.H === H && DMC.sig === sig) return DMC.m;
        let m = null;
        if (els.length) {
            const fp = new Uint8Array(W * H); let any = false;
            els.forEach(l => { try { const q = fn(l, W, H); if (q && q.length === W * H) for (let i = 0; i < q.length; i++) if (q[i]) { fp[i] = 1; any = true; } } catch (e) { warn('decal mask', e); } });
            if (any) {
                m = new Uint8Array(W * H).fill(255);
                for (let y = 0; y < H; y++) for (let x = 0, i = y * W; x < W; x++, i++) {
                    if (!fp[i]) continue;
                    m[i] = 0;
                    for (let dy = -1; dy <= 1; dy++) {
                        const yy = y + dy; if (yy < 0 || yy >= H) continue;
                        for (let dx = -1; dx <= 1; dx++) { const xx = x + dx; if (xx < 0 || xx >= W) continue; const j = yy * W + xx; if (!fp[j]) m[j] = 128; }
                    }
                }
            }
        }
        DMC = { id: m ? ++DMSEQ : 0, rev, W, H, sig, m }; return m;
    }
    const ECACHE = new WeakMap();
    // the clip a fade really uses: its own area (selection / zone clip, may be null) x outside the decals (when "Keep decals" is on)
    function effClip(rec, sp, base) {
        if (rec && rec.keepDecals === false) return base || null;
        const dm = decalMask(sp); if (!dm) return base || null;
        if (!base) return dm;
        const hit = ECACHE.get(base); if (hit && hit.dm === dm) return hit.out;
        const out = new Uint8Array(dm.length);
        for (let i = 0; i < out.length; i++) { const b = base[i]; if (b) out[i] = b === 255 ? dm[i] : ((b * dm[i] + 127) / 255) | 0; }
        ECACHE.set(base, { dm, out }); return out;
    }
    function decalSigOf(rec, sp) { if (rec && rec.keepDecals === false) return 'x'; decalMask(sp); return DMC ? DMC.id : 0; }
    // a frozen fade (see "project round trip") is drawn from its own saved field, not from the car model
    function recLive(rec, sp) {
        if (!rec) return false;
        if (rec.frozen) return rec.frozen.size[0] === sp.W && rec.frozen.size[1] === sp.H && (!rec.frozen.plist || rec.frozen.plist === plistOf(sp.key));
        return !rec.key || rec.key === sp.key;
    }
    function plistOf(key) { return String(key || '').split('|')[3] || ''; }
    function drawRec(rec, sp, stride, clip) {
        if (!recLive(rec, sp)) return;
        if (rec.frozen) {
            if (rec.frozen.empty) return;
            RF().previewField(sp, rec.frozen, previewStops(rec), { stride, into, keep: true, clip: effClip(rec, sp, null) });
            return;
        }
        RF().preview(sp, rec.dir, partsOf(rec, sp), previewStops(rec), { stride, into, keep: true, clip: effClip(rec, sp, clip) });
    }
    function drawOverlay(stride) {
        raf = 0;
        const r = RF(), sp = r && r.cur(); if (!sp || !panel || panel.style.display === 'none') return;
        const ov = ensureOverlay(); if (!ov) return;
        const w = Math.ceil(sp.W / stride), h = Math.ceil(sp.H / stride);
        if (!into || into.width !== w || into.height !== h) into = new ImageData(w, h);
        into.data.fill(0);
        S.recs.forEach(rec => { if (D && D.id === rec.id) return; drawRec(rec, sp, stride, rec.clip); });
        if (D) drawRec(D, sp, stride, liveClip());
        const ctx = ov.getContext('2d');
        ctx.clearRect(0, 0, ov.width, ov.height);
        if (stride === 1 && ov.width === w && ov.height === h) ctx.putImageData(into, 0, 0);
        else {
            if (!tmpCv) tmpCv = doc.createElement('canvas');
            tmpCv.width = w; tmpCv.height = h; tmpCv.getContext('2d').putImageData(into, 0, 0);
            ctx.imageSmoothingEnabled = false; ctx.drawImage(tmpCv, 0, 0, ov.width, ov.height);
        }
        drawHandles(ctx);
        ov.style.display = '';
    }
    function drawHandles(ctx) {
        if (!D || D.dir.kind !== 'custom' || !D.dir.custom) return;
        const c = D.dir.custom, pc = doc.getElementById('paintCanvas'), k = pc && pc.offsetWidth ? pc.width / pc.offsetWidth : 1;
        const pts = [c.p1, c.p2].filter(Boolean); if (!pts.length) return;
        ctx.save(); ctx.lineCap = 'round';
        if (pts.length === 2) {
            [[5 * k, 'rgba(0,0,0,.75)'], [2.4 * k, '#ffffff']].forEach(a => { ctx.lineWidth = a[0]; ctx.strokeStyle = a[1]; ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); ctx.lineTo(pts[1][0], pts[1][1]); ctx.stroke(); });
            const ang = Math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0]), hl = 16 * k;
            ctx.fillStyle = '#ffffff'; ctx.strokeStyle = 'rgba(0,0,0,.75)'; ctx.lineWidth = 1.5 * k;
            ctx.beginPath(); ctx.moveTo(pts[1][0], pts[1][1]); ctx.lineTo(pts[1][0] - hl * Math.cos(ang - 0.45), pts[1][1] - hl * Math.sin(ang - 0.45)); ctx.lineTo(pts[1][0] - hl * Math.cos(ang + 0.45), pts[1][1] - hl * Math.sin(ang + 0.45)); ctx.closePath(); ctx.stroke(); ctx.fill();
        }
        pts.forEach((p, i) => { ctx.beginPath(); ctx.arc(p[0], p[1], 7 * k, 0, 6.2832); ctx.fillStyle = i === 0 ? '#3fbab5' : '#e0a030'; ctx.fill(); ctx.lineWidth = 2 * k; ctx.strokeStyle = '#ffffff'; ctx.stroke(); });
        ctx.restore();
    }
    function queue(stride) {
        reqStride = Math.min(reqStride || 99, stride || 1);
        if (!raf) raf = root.requestAnimationFrame(() => { const s = reqStride; reqStride = 0; drawOverlay(s); if (s > 1) { clearTimeout(settleT); settleT = setTimeout(() => queue(1), 160); } });
    }
    function hideOverlay() { if (overlay) { overlay.style.display = 'none'; overlay.classList.remove('spb-fd-pick'); try { overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height); } catch (e) {} } }

    // custom direction: two clicks (pick) + draggable dots
    function sheetPt(e) { const r = overlay.getBoundingClientRect(); return [(e.clientX - r.left) * overlay.width / r.width, (e.clientY - r.top) * overlay.height / r.height]; }
    function wireOverlay() {
        overlay.addEventListener('pointerdown', e => {   // only while picking the two points (the overlay is click-through otherwise)
            if (!pick || !D || e.button !== 0) return;
            const sp = RF().cur(); if (!sp) return;
            const p = sheetPt(e), a = sp.at(p[0], p[1]);
            e.preventDefault(); e.stopPropagation();
            if (!a) { toast('Click on a part of the car (a coloured area of the sheet).', true); return; }
            const cu = D.dir.custom = D.dir.custom || {};
            if (pick === 1) { cu.p1 = p; cu.u1 = a.u; cu.a1 = a.a; cu.p2 = null; pick = 2; setNote('Now click where the fade ends.'); }
            else { cu.p2 = p; cu.u2 = a.u; cu.a2 = a.a; pick = 0; overlay.classList.remove('spb-fd-pick'); setNote(''); }
            refreshPanel(false); queue(1);
        });
    }
    // dragging the two dots: a capturing document listener that only claims the click when it lands on a dot
    function handleHit(e) {
        if (!panel || panel.style.display === 'none' || !D || !overlay || pick || D.dir.kind !== 'custom' || !customReady(D.dir)) return -1;
        const r = overlay.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) return -1;
        const p = sheetPt(e), c = D.dir.custom, k = overlay.width / r.width, R2 = 14 * k;
        const d1 = Math.hypot(p[0] - c.p1[0], p[1] - c.p1[1]), d2 = Math.hypot(p[0] - c.p2[0], p[1] - c.p2[1]);
        return Math.min(d1, d2) <= R2 ? (d1 <= d2 ? 0 : 1) : -1;
    }
    function wireDocDrag() {
        doc.addEventListener('pointerdown', e => { if (e.button !== 0 || (panel && panel.contains(e.target))) return; const h = handleHit(e); if (h >= 0) { dragH = h; e.preventDefault(); e.stopPropagation(); } }, true);
        doc.addEventListener('pointermove', e => {
            if (dragH < 0 || !D) return;
            const sp = RF().cur(), p = sheetPt(e), a = sp && sp.at(p[0], p[1]); e.preventDefault(); if (!a) return;
            const c = D.dir.custom; if (dragH === 0) { c.p1 = p; c.u1 = a.u; c.a1 = a.a; } else { c.p2 = p; c.u2 = a.u; c.a2 = a.a; }
            queue(4);
        }, true);
        const up = () => { if (dragH >= 0) { dragH = -1; queue(1); } };
        doc.addEventListener('pointerup', up, true); doc.addEventListener('pointercancel', up, true);
    }
    function setPickMode(on) {
        pick = on ? 1 : 0;
        if (overlay) overlay.classList.toggle('spb-fd-pick', !!on);
        if (on) { if (D.dir.custom) { D.dir.custom.p1 = D.dir.custom.p2 = null; } setNote('Click where the fade starts.'); }
        queue(1);
    }
    function customReady(d) { const c = d.custom; return !!(c && c.p1 && c.p2 && isFinite(c.u1) && isFinite(c.u2)); }

    // ---------------------------------------------------------------- panel
    function ico() { return '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><rect x="1.5" y="3" width="3.2" height="10" rx=".8" fill="currentColor"/><rect x="5.6" y="3" width="3.2" height="10" rx=".8" fill="currentColor" opacity=".62"/><rect x="9.7" y="3" width="2.4" height="10" rx=".8" fill="currentColor" opacity=".34"/><rect x="13" y="3" width="1.5" height="10" rx=".7" fill="currentColor" opacity=".16"/></svg>'; }
    function buildPanel() {
        if (panel && panel.isConnected) return panel;
        panel = doc.createElement('div'); panel.id = 'spbFadePanel'; panel.className = 'spb-fd-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Car-Space Fade'); panel.style.display = 'none';
        panel.innerHTML =
            '<div class="spb-fd-ph"><span class="spb-fd-pt">' + ico() + 'Car-Space Fade</span><button type="button" class="spb-fd-x" data-k="close" title="Close (Esc). Fades you added stay." aria-label="Close">×</button></div>' +
            '<div class="spb-fd-lab">Direction</div>' +
            '<div class="spb-fd-seg" role="group" aria-label="Fade direction">' + Object.keys(DIRS).map(k => '<button type="button" data-dir="' + k + '">' + DIRS[k] + '</button>').join('') + '</div>' +
            '<div class="spb-fd-row"><button type="button" data-k="rev" aria-pressed="false" title="Swap the two ends">⇄ Reverse</button><button type="button" data-k="pick" class="spb-fd-hide" title="Click the start point, then the end point, on the car">Pick 2 points</button><span class="spb-fd-grow"></span><label for="spbFdSpan">Spread over</label><select id="spbFdSpan" data-k="span" title="Whole car: the fade runs end to end of the whole car. Chosen parts: it runs end to end of just the parts you pick."><option value="car">Whole car</option><option value="sel">Chosen parts</option></select></div>' +
            '<div class="spb-fd-note" data-r="dirnote"></div>' +
            '<div class="spb-fd-lab">Parts <button type="button" class="spb-fd-lnk" data-k="all">All</button></div>' +
            '<div class="spb-fd-chips" data-r="chips"></div>' +
            '<div class="spb-fd-row"><label class="spb-fd-chk" title="On: numbers, sponsors, logos and the Car Mandatory layer stay exactly as they are - the fade goes under them, like a stripe. Off: the fade covers everything inside the parts."><input type="checkbox" data-k="keepDecals"> Keep decals on top</label></div>' +
            '<div class="spb-fd-lab">Stops <label class="spb-fd-chk" title="Off: the fade changes only the material (the spec map), the paint colour stays"><input type="checkbox" data-k="paintOn"> Colour</label></div>' +
            '<div class="spb-fd-bar" data-r="bar"></div>' +
            '<div class="spb-fd-stops" data-r="stops"></div>' +
            '<div class="spb-fd-row"><button type="button" data-k="addstop" title="Add another stop in the widest gap">+ Stop</button><span class="spb-fd-grow"></span><span class="spb-fd-status" data-r="status"></span></div>' +
            '<div class="spb-fd-note" data-r="note"></div>' +
            '<div class="spb-fd-pb"><button type="button" data-k="close">Done</button><button type="button" data-k="apply" class="spb-fd-primary" data-r="apply">Add Fade</button></div>' +
            '<div class="spb-fd-list" data-r="list"></div>';
        doc.body.appendChild(panel);
        panel.addEventListener('click', onClick);
        panel.addEventListener('input', onInput);
        panel.addEventListener('change', onChange);
        panel.addEventListener('pointerdown', onBarDown);
        doc.addEventListener('keydown', e => { if (e.key === 'Escape' && panel && panel.style.display !== 'none') { if (pick) { setPickMode(false); setNote(''); refreshPanel(false); } else closePanel(); } });
        return panel;
    }
    function R(name) { return panel.querySelector('[data-r="' + name + '"]'); }
    function setNote(t) { if (!panel) return; const n = R('note'); if (n) n.textContent = t || ''; }
    function placePanel() {
        const a = (menuBtn && menuBtn.isConnected && (menuBtn.closest('details') || menuBtn).getBoundingClientRect()) || { left: 80, bottom: 120 };
        const w = panel.offsetWidth || 340, vw = root.innerWidth || 1200, vh = root.innerHeight || 800;
        panel.style.left = Math.max(8, Math.min(vw - w - 8, a.left)) + 'px';
        panel.style.top = Math.max(8, Math.min(vh - Math.min(panel.offsetHeight || 500, vh - 16) - 8, Math.round(a.bottom + 6))) + 'px';
        panel.style.maxHeight = (vh - 24) + 'px';
    }
    function partChipsHtml(sp) {
        const sel = new Set(D.parts && D.parts.length ? D.parts : sp.order);
        return sp.order.map(n => '<button type="button" class="spb-fd-chip" data-part="' + esc(n) + '" aria-pressed="' + (sel.has(n) ? 'true' : 'false') + '">' + esc(n) + '</button>').join('');
    }
    function gradientCss(rec) {
        const st = sortedStops(rec); if (!st.length) return '#444';
        const cols = st.map(s => {
            if (rec.paintOn) return hex6(s.color);
            const sp = s.mat !== 'keep' && s.mat !== 'finish' ? specOfMat(s.mat) : null;
            const g = sp ? Math.round(Math.min(255, 70 + sp[0] * 0.55)) : 120; return 'rgb(' + g + ',' + g + ',' + Math.min(255, g + 8) + ')';
        });
        return 'linear-gradient(90deg,' + st.map((s, i) => cols[i] + ' ' + (s.p * 100).toFixed(1) + '%').join(',') + ')';
    }
    function barHtml() {
        return '<div class="spb-fd-ramp" style="background:' + gradientCss(D) + '"></div>' +
            D.stops.map((s, i) => '<button type="button" class="spb-fd-mk" data-mk="' + i + '" style="left:' + (s.p * 100).toFixed(2) + '%;--c:' + (D.paintOn ? hex6(s.color) : '#cfd2d8') + '" title="Stop at ' + Math.round(s.p * 100) + '% - drag to move"></button>').join('');
    }
    function stopsHtml() {
        const P = presets();
        return D.stops.map((s, i) => {
            const opts = '<option value="keep"' + (s.mat === 'keep' ? ' selected' : '') + '>Keep as is</option>' + P.map(p => '<option value="' + p.id + '"' + (s.mat === p.id ? ' selected' : '') + '>' + esc(p.name) + '</option>').join('') +
                '<option value="finish"' + (s.mat === 'finish' ? ' selected' : '') + '>' + (s.mat === 'finish' && s.finish ? 'Finish: ' + esc(finName(s.finish)) : 'Finish…') + '</option>';
            const isFin = s.mat === 'finish';
            return '<div class="spb-fd-stop" data-i="' + i + '"><input type="number" class="spb-fd-pos" min="0" max="100" step="1" value="' + Math.round(s.p * 100) + '" data-sk="p" aria-label="Stop position in percent"><span class="spb-fd-u">%</span>' +
                '<input type="color" class="spb-fd-col" value="' + hex6(s.color) + '" data-sk="color" aria-label="Stop colour"' + (!D.paintOn || isFin ? ' disabled' : '') + (isFin ? ' title="A finish brings its own colour"' : '') + '>' +
                '<select data-sk="mat" class="spb-fd-mat" aria-label="Material at this stop">' + opts + '</select>' +
                (isFin ? '<button type="button" class="spb-fd-fin" data-sk="fin" title="Choose another finish" aria-label="Choose another finish">…</button>' : '') +
                '<button type="button" class="spb-fd-del" data-sk="del" title="Remove this stop" aria-label="Remove this stop"' + (D.stops.length <= 2 ? ' disabled' : '') + '>×</button></div>';
        }).join('');
    }
    function listHtml(sp) {
        const mine = S.recs.filter(r => recLive(r, sp));
        if (!mine.length) return '';
        return '<div class="spb-fd-lab">Fades on this car</div>' + mine.map((r, i) => '<div class="spb-fd-item' + (D && D.id === r.id ? ' spb-fd-cur' : '') + '" data-fid="' + esc(r.id) + '"><span class="spb-fd-sw" style="background:' + gradientCss(r) + '"></span><span class="spb-fd-nm" title="' + esc(describe(r)) + '">' + (i + 1) + '. ' + esc(r.name) + '</span><button type="button" data-fa="edit">Edit</button><button type="button" data-fa="del" aria-label="Remove fade">Remove</button></div>').join('');
    }
    function refreshPanel(full) {
        if (!panel || !D) return;
        const sp = RF().cur(); if (!sp) return;
        panel.querySelectorAll('[data-dir]').forEach(b => b.setAttribute('aria-pressed', b.getAttribute('data-dir') === D.dir.kind ? 'true' : 'false'));
        panel.querySelector('[data-k="rev"]').setAttribute('aria-pressed', D.dir.rev ? 'true' : 'false');
        panel.querySelector('[data-k="pick"]').classList.toggle('spb-fd-hide', D.dir.kind !== 'custom');
        panel.querySelector('[data-k="rev"]').classList.toggle('spb-fd-hide', D.dir.kind === 'custom' && false);
        panel.querySelector('[data-k="span"]').value = D.dir.span || 'car';
        panel.querySelector('[data-k="paintOn"]').checked = !!D.paintOn;
        panel.querySelector('[data-k="keepDecals"]').checked = D.keepDecals !== false;
        if (!pick) { const dn = R('dirnote'); dn.textContent = D.dir.kind === 'custom' && !customReady(D.dir) ? 'Use "Pick 2 points", then click the start and the end of the fade on the car.' : DIR_TIPS[D.dir.kind]; }
        if (full !== false) { R('chips').innerHTML = partChipsHtml(sp); R('stops').innerHTML = stopsHtml(); R('list').innerHTML = listHtml(sp); }
        R('bar').innerHTML = barHtml();
        const ap = R('apply'); ap.textContent = D.id ? 'Update Fade' : 'Add Fade';
        const ready = D.dir.kind !== 'custom' || customReady(D.dir);
        ap.disabled = !ready; ap.title = ready ? '' : 'Pick the start and end points first';
        const w = sp.info && sp.info.warn && sp.info.warn.length ? sp.info.warn[0] : '';
        R('status').textContent = w ? w : '';
    }
    function setDirKind(k) {
        D.dir.kind = k;
        if (k === 'custom') { if (!customReady(D.dir)) { refreshPanel(false); setPickMode(true); return; } }
        else setPickMode(false);
        refreshPanel(false); queue(1);
    }
    function onClick(e) {
        const t = e.target; if (!t || !t.closest) return;
        const dirb = t.closest('[data-dir]'); if (dirb) { e.preventDefault(); setDirKind(dirb.getAttribute('data-dir')); return; }
        const chip = t.closest('[data-part]');
        if (chip) {
            e.preventDefault(); const sp = RF().cur(), n = chip.getAttribute('data-part');
            let arr = D.parts && D.parts.length ? D.parts.slice() : sp.order.slice();
            if (arr.indexOf(n) >= 0) { if (arr.length === 1) { toast('Keep at least one part.', true); return; } arr = arr.filter(x => x !== n); } else arr.push(n);
            D.parts = arr.length === sp.order.length ? null : sp.order.filter(x => arr.indexOf(x) >= 0);
            R('chips').innerHTML = partChipsHtml(sp); queue(1); return;
        }
        const fa = t.closest('[data-fa]');
        if (fa) {
            e.preventDefault(); const id = fa.closest('[data-fid]').getAttribute('data-fid');
            if (fa.getAttribute('data-fa') === 'del') removeFade(id); else editFade(id);
            return;
        }
        const sk = t.closest('[data-sk]');
        if (sk) {
            const i = +sk.closest('[data-i]').getAttribute('data-i'), k = sk.getAttribute('data-sk');
            if (k === 'del' && D.stops.length > 2) { e.preventDefault(); D.stops.splice(i, 1); refreshPanel(true); queue(1); }
            else if (k === 'fin') { e.preventDefault(); openFinishPicker(i); }
            return;
        }
        const b = t.closest('[data-k]'); if (!b) return;
        const k = b.getAttribute('data-k');
        if (k === 'close') { e.preventDefault(); closePanel(); }
        else if (k === 'apply') { e.preventDefault(); commit(); }
        else if (k === 'rev') { e.preventDefault(); D.dir.rev = !D.dir.rev; refreshPanel(false); queue(1); }
        else if (k === 'pick') { e.preventDefault(); setPickMode(true); refreshPanel(false); }
        else if (k === 'all') { e.preventDefault(); D.parts = null; R('chips').innerHTML = partChipsHtml(RF().cur()); queue(1); }
        else if (k === 'addstop') { e.preventDefault(); addStop(); }
    }
    function onInput(e) {
        const t = e.target, sk = t.getAttribute && t.getAttribute('data-sk'); if (!sk || !D) return;
        const i = +t.closest('[data-i]').getAttribute('data-i'), s = D.stops[i]; if (!s) return;
        if (sk === 'p') { const v = Math.max(0, Math.min(100, +t.value)); if (isFinite(v)) { s.p = v / 100; R('bar').innerHTML = barHtml(); queue(2); } }
        else if (sk === 'color') { s.color = hex6(t.value); R('bar').innerHTML = barHtml(); queue(1); }
    }
    function onChange(e) {
        const t = e.target; if (!t || !D) return;
        const k = t.getAttribute('data-k'), sk = t.getAttribute('data-sk');
        if (k === 'span') { D.dir.span = t.value; queue(1); }
        else if (k === 'paintOn') { D.paintOn = !!t.checked; refreshPanel(true); queue(1); }
        else if (k === 'keepDecals') { D.keepDecals = !!t.checked; queue(1); }
        else if (sk === 'p') { D.stops.sort((a, b) => a.p - b.p); refreshPanel(true); queue(1); }
        else if (sk === 'mat') {
            const i = +t.closest('[data-i]').getAttribute('data-i'), s = D.stops[i];
            if (t.value === 'finish') { s.mat = 'finish'; refreshPanel(true); openFinishPicker(i); }
            else { s.mat = t.value; refreshPanel(true); queue(1); }
        }
    }
    function addStop() {
        if (D.stops.length >= 6) { toast('Six stops is the most.', true); return; }
        const st = sortedStops(D); let bi = 0, bg = -1;
        for (let i = 0; i < st.length - 1; i++) { const g = st[i + 1].p - st[i].p; if (g > bg) { bg = g; bi = i; } }
        const a = st[bi], b = st[bi + 1], ra = rgbOf(a.color), rb = rgbOf(b.color);
        D.stops.push({ p: (a.p + b.p) / 2, color: hexOf(ra.map((v, c) => (v + rb[c]) / 2)), mat: 'keep', finish: null });
        D.stops.sort((x, y) => x.p - y.p); refreshPanel(true); queue(1);
    }
    // draggable markers on the gradient bar
    function onBarDown(e) {
        const mk = e.target.closest && e.target.closest('[data-mk]'); if (!mk || !D || e.button !== 0) return;
        e.preventDefault();
        const i = +mk.getAttribute('data-mk'), bar = R('bar'), rect = bar.getBoundingClientRect(), s = D.stops[i];
        const move = ev => { s.p = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width)); R('bar').innerHTML = barHtml(); const nb = R('bar').querySelector('[data-mk="' + i + '"]'); if (nb) nb.classList.add('spb-fd-drag'); const inp = panel.querySelector('.spb-fd-stop[data-i="' + i + '"] .spb-fd-pos'); if (inp) inp.value = Math.round(s.p * 100); queue(2); };
        const up = () => { doc.removeEventListener('pointermove', move); doc.removeEventListener('pointerup', up); doc.removeEventListener('pointercancel', up); D.stops.sort((a, b) => a.p - b.p); refreshPanel(true); queue(1); };
        doc.addEventListener('pointermove', move); doc.addEventListener('pointerup', up); doc.addEventListener('pointercancel', up);
    }

    // finish picker (the app's own), as the Material Brush does it
    function openFinishPicker(i) {
        finTarget = i;
        const btn = panel.querySelector('.spb-fd-stop[data-i="' + i + '"] [data-sk="fin"]') || panel.querySelector('.spb-fd-stop[data-i="' + i + '"] [data-sk="mat"]');
        wrapPicker();
        if (typeof root.openSwatchPicker !== 'function') { toast('The finish picker is not available here.', true); return; }
        let zi = 0; try { zi = (typeof selectedZoneIndex === 'number' && zones[selectedZoneIndex]) ? selectedZoneIndex : 0; } catch (e) {}
        pickerBtn = btn; root.openSwatchPicker(btn, 'base', zi);
    }
    let pickerBtn = null;
    function wrapPicker() {
        const cur = root.selectSwatchItem;
        if (typeof cur !== 'function' || cur.__spbRevFade) return;
        const w = function (id) {
            try {
                if (pickerBtn && finTarget >= 0 && typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.open && swatchPopupState.triggerEl === pickerBtn) {
                    if (id && id !== 'none' && id !== 'dualshift_custom' && D && D.stops[finTarget]) {
                        D.stops[finTarget].mat = 'finish'; D.stops[finTarget].finish = String(id);
                        if (typeof _spbBumpFinishUsage === 'function') _spbBumpFinishUsage(id);
                    }
                    if (typeof root.closeSwatchPicker === 'function') root.closeSwatchPicker();
                    finTarget = -1; pickerBtn = null;
                    refreshPanel(true); queue(1);
                    return;
                }
            } catch (e) { warn('picker', e); }
            return cur.apply(this, arguments);
        };
        w.__spbRevFade = true; root.selectSwatchItem = w;
    }

    // ---------------------------------------------------------------- records, undo, payload
    function snap() { return S.recs.slice(); }
    function pushUndo(label, before, after) {
        S.undo.push({ label, before, after }); if (S.undo.length > UNDO_MAX) S.undo.shift();
        S.redo.length = 0;
        try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (e) {}
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (e) {}
    }
    function changed() {
        S.gen++; emit('changed');
        clearTimeout(changed.t);
        changed.t = setTimeout(() => {
            try { const MM = MAT(); if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); } catch (e) {}
            if (panel && panel.style.display !== 'none') { refreshPanel(true); queue(1); }
            refreshMenu();
        }, 30);
    }
    function applySnap(a) { S.recs = a.slice(); if (D && D.id && !S.recs.some(r => r.id === D.id)) D.id = null; changed(); }
    function undo() { const e = S.undo.pop(); if (!e) return false; applySnap(e.before); S.redo.push(e); return true; }
    function redo() { const e = S.redo.pop(); if (!e) return false; applySnap(e.after); S.undo.push(e); return true; }
    function registerUndo() {
        if (!root.SPBUndoExt) return;
        root.SPBUndoExt.register(KIND, {
            hasUndo: () => S.undo.length > 0, hasRedo: () => S.redo.length > 0, undo, redo,
            clearRedo: () => { S.redo.length = 0; }, label: () => { const e = S.undo[S.undo.length - 1]; return e ? e.label : 'Car-Space Fade'; }
        });
    }
    function commit() {
        const r = RF(), sp = r && r.cur(); if (!sp || !D) return null;
        if (D.dir.kind === 'custom' && !customReady(D.dir)) { toast('Pick the start and end points on the car first.', true); return null; }
        if (!D.paintOn && D.stops.every(s => s.mat === 'keep')) { toast('Turn Colour on or give a stop a material (Chrome, Matte, a finish...) - otherwise there is nothing to fade.', true); return null; }
        const rec = cloneRec(D);
        rec.key = sp.key; rec.id = D.id || ('fd' + (++S.seq)); rec.name = autoName(rec); rec.clip = null;
        const cl = liveClip(); if (cl) rec.clip = new Uint8Array(cl);
        rec.stops.sort((a, b) => a.p - b.p);
        const before = snap(); let after;
        const at = S.recs.findIndex(x => x.id === rec.id);
        if (at >= 0) { after = before.slice(); after[at] = rec; } else after = before.concat([rec]);
        pushUndo(at >= 0 ? 'Edit Car-Space Fade' : 'Add Car-Space Fade', before, after);
        S.recs = after; changed();
        toast((at >= 0 ? 'Fade updated: ' : 'Fade added: ') + rec.name + '. Live Preview and RENDER use it. Reopen the panel to edit or remove it.');
        D = newDraft(); D.stops = rec.stops.map(cloneStop); D.dir = cloneDir(rec.dir); D.parts = rec.parts ? rec.parts.slice() : null; D.paintOn = rec.paintOn; D.keepDecals = rec.keepDecals !== false;
        closePanel(); return rec;
    }
    function removeFade(id) {
        const before = snap(), after = before.filter(r => r.id !== id); if (after.length === before.length) return;
        pushUndo('Remove Car-Space Fade', before, after); S.recs = after;
        if (D && D.id === id) { D.id = null; }
        changed();
    }
    function editFade(id) {
        const rec = S.recs.find(r => r.id === id); if (!rec) return;
        D = cloneRec(rec); setPickMode(false); refreshPanel(true); queue(1);
    }
    function pngOf(w, h, fill) {
        const cv = doc.createElement('canvas'); cv.width = w; cv.height = h;
        const ctx = cv.getContext('2d'), id = ctx.createImageData(w, h); fill(id.data); ctx.putImageData(id, 0, 0);
        return cv.toDataURL('image/png');
    }
    function encodeRec(rec, sp) {
        const dsig = decalSigOf(rec, sp), hit = ENC.get(rec); if (hit && hit.key === sp.key && hit.ds === dsig) return hit.out;
        if (rec.frozen) { const o = encodeFrozen(rec, sp); ENC.set(rec, { key: sp.key, ds: dsig, out: o }); return o; }
        const f = RF().field(sp, rec.dir, partsOf(rec, sp), effClip(rec, sp, rec.clip || null), { ts: 4 });
        let out = null;
        if (f) {
            const bw = f.bbox[2], bh = f.bbox[3];
            out = {
                bbox: f.bbox, ts: f.ts,
                t: pngOf(f.tw, f.th, d => { for (let i = 0, o = 0; i < f.t16.length; i++, o += 4) { const v = f.t16[i]; d[o] = v >> 8; d[o + 1] = v & 255; d[o + 2] = 0; d[o + 3] = 255; } }),
                cov: pngOf(bw, bh, d => { for (let i = 0, o = 0; i < f.cov.length; i++, o += 4) { const v = f.cov[i]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; } })
            };
        }
        ENC.set(rec, { key: sp.key, ds: dsig, out }); return out;
    }
    function finishZone(s, orig) {
        const M = MAT(); if (!s.finish || !M || !M.makeCoatZone || typeof orig !== 'function') return null;
        if (s._zc && s._zc.id === s.finish) return s._zc.zone;
        let zo = null;
        try {
            const z = M.makeCoatZone(s.finish);
            if (z) {
                // sheet size from the Car-Space model, NOT M.state.W/H (0 until a Material tool has been used -> an empty region -> a null zone -> a finish stop that silently did nothing; found by t_gates2)
                const sp0 = RF() && RF().cur(), W = sp0 ? sp0.W : 2048, H = sp0 ? sp0.H : 2048, rm = new Uint8Array(W * H); rm[0] = 255;   // a one-pixel region: the engine swaps in the real coverage
                z.regionMask = rm; z.useRegion = true; z.hardEdge = true; z.muted = false;
                const made = orig([z]); zo = made && made[0] ? made[0] : null;
            }
        } catch (e) { warn('finish zone', e); }
        s._zc = { id: s.finish, zone: zo }; return zo;
    }
    function fadePayload(orig) {
        const r = RF(), sp = r && r.cur(); if (!sp) return [];
        const out = [];
        S.recs.forEach(rec => {
            if (!recLive(rec, sp)) return;
            const e = encodeRec(rec, sp); if (!e) return;
            const stops = sortedStops(rec).map(s => {
                const o = { p: +Math.max(0, Math.min(1, s.p)).toFixed(5), color: null, spec: null, zone: null };
                if (s.mat === 'finish') o.zone = finishZone(s, orig);
                else { if (rec.paintOn) o.color = rgbOf(s.color); if (s.mat !== 'keep') o.spec = specOfMat(s.mat); }
                return o;
            });
            out.push({ v: 1, size: [sp.W, sp.H], bbox: e.bbox, ts: e.ts, cov: e.cov, t: e.t, paint: !!rec.paintOn, stops });
        });
        return out;
    }
    function payload(orig) { const l = fadePayload(orig || (root.buildServerZonesForRender && (root.buildServerZonesForRender.__spbRevFadeOrig || root.buildServerZonesForRender))); return l; }
    function wrapSerializer() {
        const cur = root.buildServerZonesForRender;
        if (typeof cur !== 'function') return false;
        if (cur.__spbRevFade) return true;
        const orig = cur;
        const w = function (zs) {
            const out = orig.apply(this, arguments);
            try {
                if (off() || !S.recs.length || !Array.isArray(out) || !out.length || typeof zones === 'undefined' || zs !== zones) return out;
                const list = fadePayload(orig); if (!list.length) return out;
                const sp = RF().cur(), lay = out[0]._spb_rev_material || { v: 1, size: [sp.W, sp.H] };
                lay.fade = list; out[0]._spb_rev_material = lay;
            } catch (e) { warn('payload skipped', e); }
            return out;
        };
        w.__spbRevFade = true; w.__spbRevFadeOrig = orig; if (cur.__spbRevMatOrig) w.__spbRevMatOrig = cur.__spbRevMatOrig;
        // [SPB-REV-FADE 2026-10-10] REV-SPONSOR integration bug: LayerMat's wrap check is `cur.__spbLayerMat`; without this copy, LayerMat and Fade re-wrapped each other forever
        // (31+ identical coat zones, a 1.6 MB payload, a crashed page). Copying the flag keeps both timers satisfied in either wrap order. Kill switch SPB_REV_FADE_OFF still applies to the wrapper itself.
        if (cur.__spbLayerMat) w.__spbLayerMat = true;
        root.buildServerZonesForRender = w; return true;
    }

    // ---------------------------------------------------------------- menu entry + open / close
    const MENU_HTML = '<span class="spb-mi-ico spb-sym-ico">' + ico() + '</span> Car-Space Fade…';
    function ensureMenuBtn() {
        if (off()) { if (menuBtn) menuBtn.style.display = 'none'; return false; }
        const pop = doc.querySelector('#spbSymMenu .spb-tb-pop'); if (!pop) return false;
        if (menuBtn && menuBtn.parentNode === pop) return true;
        menuBtn = doc.createElement('button'); menuBtn.type = 'button'; menuBtn.className = 'vtool-btn'; menuBtn.id = 'spbFadeMenuBtn';
        menuBtn.title = 'A colour and material fade that runs along the car, not the flat sheet: left and right sides match, hood, roof and trunk carry on across the seams.';
        menuBtn.innerHTML = MENU_HTML;
        const after = pop.querySelector('[data-sym="stripe"]');
        if (after && after.parentNode === pop) pop.insertBefore(menuBtn, after.nextSibling); else pop.appendChild(menuBtn);
        menuBtn.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); const d = menuBtn.closest('details'); if (d) d.removeAttribute('open'); openPanel(); });
        refreshMenu(); return true;
    }
    function refreshMenu() { if (!menuBtn) return; const n = S.recs.length; menuBtn.innerHTML = MENU_HTML + (n ? ' <span class="spb-fd-cnt">' + n + '</span>' : ''); }
    async function ensureSpace() {
        const r = RF(); if (!r) return null;
        try { if (root.SpbProCar && root.SpbProCar.ensure) await root.SpbProCar.ensure(false); } catch (e) {}
        return await r.build(false);
    }
    async function openPanel() {
        if (off() || spaceBusy) return false;
        buildPanel(); spaceBusy = true;
        panel.style.display = ''; placePanel(); R('status').textContent = 'Measuring the car…';
        let sp = null;
        try { sp = await ensureSpace(); } catch (e) { warn('space', e); }
        spaceBusy = false;
        if (!sp) { closePanel(); toast('Car-Space Fade could not line this car up (load the car and its template first).', true); return false; }
        if (!D) D = newDraft();
        if (!D.stops || D.stops.length < 2) D = newDraft();
        refreshPanel(true); placePanel(); queue(1);
        const first = panel.querySelector('[data-dir][aria-pressed="true"]'); if (first) try { first.focus({ preventScroll: true }); } catch (e) {}
        return true;
    }
    function closePanel() {
        setPickMode(false);
        if (panel) panel.style.display = 'none';
        hideOverlay(); clearTimeout(settleT);
    }

    // ---------------------------------------------------------------- init
    function init() {
        if (off()) return;
        registerUndo();
        wireDocDrag();
        // keep the panel inside the window when it is resized / the browser zoom changes while the panel is open (found at 1100x800 by t_gates1)
        root.addEventListener('resize', function () { if (panel && panel.isConnected && panel.style.display !== 'none') { placePanel(); syncOverlay(); } });
        wrapSerializer();
        let tries = 0;
        const t = setInterval(() => { wrapSerializer(); ensureMenuBtn(); if (++tries > 90) clearInterval(t); }, 700);
        doc.addEventListener('toggle', e => { if (e.target && e.target.id === 'spbSymMenu') ensureMenuBtn(); }, true);
        ensureMenuBtn();
    }
    // programmatic use (tests, MCP): add a fade without the panel
    async function addFade(opts) {
        const sp = await ensureSpace(); if (!sp) return null;
        D = newDraft(); const o = opts || {};
        if (o.dir) D.dir = Object.assign(D.dir, o.dir);
        if (o.parts) D.parts = o.parts.slice();
        if (o.paintOn != null) D.paintOn = !!o.paintOn;
        if (o.keepDecals != null) D.keepDecals = !!o.keepDecals;
        if (o.stops) D.stops = o.stops.map(s => ({ p: s.p, color: hex6(s.color || '#808080'), mat: s.mat || 'keep', finish: s.finish || null }));
        panel = panel || buildPanel(); const prev = panel.style.display; panel.style.display = 'none';
        const rec = commit(); return rec ? { id: rec.id, name: rec.name } : null;
    }
    // ---------------------------------------------------------------- project round trip
    // [SPB-REV-FADE 2026-10-10 FADE-2] serialize() -> ONE plain JSON-able object (or null when there are no fades), restore(obj) puts it back; js/features/spb-projects.js
    // stores it in the optional project field `revFade` (a project without fades is byte-for-byte what it was, like REV-MATERIAL's `revMaterial`).
    //   {v:1, size:[W,H], seq, recs:[{id, key, name, dir, parts, paintOn, keepDecals, stops:[{p,color,mat,finish}], clip:{bbox:[x,y,w,h], png}|null}]}
    // A record is its own settings (a few hundred bytes) plus, only when it was added inside a selection / zone clip, that clip as a bbox-cropped 8-bit gray PNG
    // (lossless). The t-field and the coverage are NOT stored: they are recomputed from the car model, so the render after a re-open is the same bytes.
    // restore() is all-or-nothing, rebinds the records to the current car model (a project always opens on its own car) and starts the undo history fresh
    // (old entries would point at records that no longer exist). Kill switch: SPB_REV_FADE_OFF (off() above) - serialize() then returns null.
    const CPC = new WeakMap(); let restoreGen = 0;
    function encodeClip(clip, W, H) {
        if (!clip) return null;
        const hit = CPC.get(clip); if (hit) return hit;
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        for (let y = 0; y < H; y++) { const s = y * W; for (let x = 0; x < W; x++) if (clip[s + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
        let out;
        if (x1 < 0) out = { bbox: [0, 0, 0, 0], png: null };                   // an all-zero clip (nothing allowed) stays all-zero
        else {
            const bw = x1 - x0 + 1, bh = y1 - y0 + 1;
            out = { bbox: [x0, y0, bw, bh], png: pngOf(bw, bh, d => { for (let y = 0; y < bh; y++) { let s = (y + y0) * W + x0, o = y * bw * 4; for (let x = 0; x < bw; x++, s++, o += 4) { const v = clip[s]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; } } }) };
        }
        CPC.set(clip, out); return out;
    }
    function decodeImage(url) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error('a saved fade area did not decode')); im.src = url; }); }
    async function decodeClip(c, W, H) {
        if (!c) return null;
        const out = new Uint8Array(W * H); if (!c.png) return out;
        const im = await decodeImage(c.png), bw = c.bbox[2], bh = c.bbox[3];
        const cv = doc.createElement('canvas'); cv.width = bw; cv.height = bh; const x = cv.getContext('2d', { willReadFrequently: true }); x.drawImage(im, 0, 0);
        const d = x.getImageData(0, 0, bw, bh).data;
        for (let y = 0; y < bh; y++) { let s = (y + c.bbox[1]) * W + c.bbox[0], o = y * bw * 4; for (let k = 0; k < bw; k++, s++, o += 4) out[s] = d[o]; }
        return out;
    }
    // FROZEN fades. The car model (js/rev/symmetry) is rebuilt from the re-opened document, and its part outlines can move by tens of pixels at a border (the template mask
    // is read from the PSD file in a fresh session but from the restored Mask layer after a project open), so a fade recomputed on the new model would not render the same bytes.
    // A saved fade therefore also carries the exact t-field + coverage it was rendered with (`fz`, before the decal weighting, which is always applied live to the CURRENT layers,
    // so a decal added after the re-open is protected too). A re-opened fade uses them as they are - drawn by previewField, sent to the engine by encodeFrozen - until it is
    // edited: "Update Fade" re-measures the car like a new fade. Kill switch: SPB_REV_FADE_NOFREEZE = true saves no `fz` (the fade is then recomputed on re-open).
    const FZC = new WeakMap();
    function tPngOf(f) { return pngOf(f.tw, f.th, d => { for (let i = 0, o = 0; i < f.t16.length; i++, o += 4) { const v = f.t16[i]; d[o] = v >> 8; d[o + 1] = v & 255; d[o + 2] = 0; d[o + 3] = 255; } }); }
    function covPngOf(f) { return pngOf(f.bbox[2], f.bbox[3], d => { for (let i = 0, o = 0; i < f.cov.length; i++, o += 4) { const v = f.cov[i]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; } }); }
    function frozenOf(rec, sp) {
        if (root.SPB_REV_FADE_NOFREEZE) return undefined;
        const z = rec.frozen;
        if (z) return z.empty ? { size: z.size.slice(), plist: z.plist || '', empty: true } : { size: z.size.slice(), plist: z.plist || '', bbox: z.bbox.slice(), ts: z.ts, tw: z.tw, th: z.th, t: z.tUrl, cov: z.covUrl };
        if (!sp || (rec.key && rec.key !== sp.key)) return undefined;
        const hit = FZC.get(rec); if (hit && hit.key === sp.key) return hit.out;
        const f = RF().field(sp, rec.dir, partsOf(rec, sp), rec.clip || null, { ts: 4 });
        const out = f ? { size: [sp.W, sp.H], plist: plistOf(sp.key), bbox: f.bbox.slice(), ts: f.ts, tw: f.tw, th: f.th, t: tPngOf(f), cov: covPngOf(f) } : { size: [sp.W, sp.H], plist: plistOf(sp.key), empty: true };
        FZC.set(rec, { key: sp.key, out }); return out;
    }
    async function decodeFrozen(fz, W, H) {
        if (!fz || !Array.isArray(fz.size) || fz.size[0] !== W || fz.size[1] !== H) return null;
        if (fz.empty) return { size: [W, H], plist: fz.plist || '', empty: true };
        const bb = fz.bbox; if (!Array.isArray(bb) || bb.length !== 4 || bb[0] < 0 || bb[1] < 0 || bb[0] + bb[2] > W || bb[1] + bb[3] > H || !(fz.ts > 0) || !fz.t || !fz.cov) return null;
        const [ti, ci] = await Promise.all([decodeImage(fz.t), decodeImage(fz.cov)]);
        if (ti.width !== fz.tw || ti.height !== fz.th || ci.width !== bb[2] || ci.height !== bb[3]) return null;
        const px = (im) => { const cv = doc.createElement('canvas'); cv.width = im.width; cv.height = im.height; const x = cv.getContext('2d', { willReadFrequently: true }); x.drawImage(im, 0, 0); return x.getImageData(0, 0, im.width, im.height).data; };
        const td = px(ti), cd = px(ci), t16 = new Uint16Array(fz.tw * fz.th), cov = new Uint8Array(bb[2] * bb[3]);
        for (let i = 0, o = 0; i < t16.length; i++, o += 4) t16[i] = (td[o] << 8) | td[o + 1];
        for (let i = 0, o = 0; i < cov.length; i++, o += 4) cov[i] = cd[o];
        return { size: [W, H], plist: fz.plist || '', bbox: bb.slice(), ts: fz.ts, tw: fz.tw, th: fz.th, t16, cov, tUrl: fz.t, covUrl: fz.cov };
    }
    // coverage of a frozen fade = its saved coverage x outside-the-decals, with the same arithmetic as effClip (an unchanged document gives the bytes it gave before the save)
    function encodeFrozen(rec, sp) {
        const fz = rec.frozen; if (!fz || fz.empty) return null;
        const bx = fz.bbox[0], by = fz.bbox[1], bw = fz.bbox[2], bh = fz.bbox[3], dm = rec.keepDecals === false ? null : decalMask(sp);
        let covUrl = fz.covUrl;
        if (dm) {
            const W = sp.W; let any = false;
            covUrl = pngOf(bw, bh, d => {
                for (let y = 0; y < bh; y++) for (let x = 0, i = y * bw, o = i * 4; x < bw; x++, i++, o += 4) {
                    const b = fz.cov[i]; let v = 0;
                    if (b) { const m = dm[(y + by) * W + x + bx]; v = b === 255 ? m : ((b * m + 127) / 255) | 0; }
                    if (v) any = true; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255;
                }
            });
            if (!any) return null;
        }
        return { bbox: fz.bbox.slice(), ts: fz.ts, t: fz.tUrl, cov: covUrl };
    }
    function serialize() {
        if (off() || !S.recs.length) return null;
        const sp = RF() && RF().cur(), W = sp ? sp.W : 2048, H = sp ? sp.H : 2048;
        return {
            v: 1, size: [W, H], seq: S.seq,
            recs: S.recs.map(r => ({ id: r.id, key: r.key, name: r.name, dir: cloneDir(r.dir), parts: r.parts ? r.parts.slice() : null, paintOn: !!r.paintOn, keepDecals: r.keepDecals !== false,
                stops: sortedStops(r).map(cloneStop), clip: encodeClip(r.clip, W, H), fz: frozenOf(r, sp) }))
        };
    }
    function adoptRecs(recs, seq) {
        S.recs = recs; S.undo.length = 0; S.redo.length = 0;
        let mx = S.seq || 0; recs.forEach(r => { const n = +String(r.id || '').replace(/^\D+/, ''); if (n > mx) mx = n; }); S.seq = Math.max(mx, seq || 0);
        if (D && D.id) D.id = null;
        changed();
    }
    async function restore(obj) {
        if (off()) return { ok: true, n: 0 };
        const my = ++restoreGen;
        try {
            if (!obj || !Array.isArray(obj.recs) || !obj.recs.length) { if (S.recs.length) adoptRecs([], 0); return { ok: true, n: 0 }; }   // a document without fades empties the previous one's
            const W = obj.size && obj.size[0], H = obj.size && obj.size[1];
            if (!(W > 0 && H > 0)) return { ok: false, why: 'the saved fades have no sheet size' };
            const recs = [];
            for (const o of obj.recs) {
                if (!o || !o.dir || !Array.isArray(o.stops) || o.stops.length < 2) return { ok: false, why: 'a saved fade is incomplete' };
                recs.push({ id: String(o.id), key: o.key || null, name: o.name || '', dir: cloneDir(o.dir), parts: o.parts ? o.parts.slice() : null, paintOn: !!o.paintOn, keepDecals: o.keepDecals !== false,
                    stops: o.stops.map(cloneStop), clip: await decodeClip(o.clip, W, H), frozen: o.fz ? await decodeFrozen(o.fz, W, H) : null });
                if (!recs[recs.length - 1].frozen) delete recs[recs.length - 1].frozen;
            }
            let sp = null; try { sp = await ensureSpace(); } catch (e) { warn('restore space', e); }   // the model must exist, or a render without opening the panel would skip the fades
            if (my !== restoreGen) return { ok: false, why: 'superseded by a newer open' };
            if (sp && sp.W === W && sp.H === H) recs.forEach(r => { r.key = sp.key; });
            adoptRecs(recs, obj.seq);
            return { ok: true, n: recs.length, bound: !!(sp && sp.W === W && sp.H === H) };
        } catch (e) { warn('restore', e); return { ok: false, why: String(e && e.message || e) }; }
    }
    root.SpbRevFadeUI = {
        version: VER, KIND, state: S, open: openPanel, close: closePanel, addFade, undo, redo, payload, fadePayload, wrapSerializer, removeFade,
        draft: () => D, setDraft: d => { D = d; }, redraw: () => queue(1), on: f => S.listeners.push(f), encodeRec, previewStops, describe, decalMask, effClip, serialize, restore
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
