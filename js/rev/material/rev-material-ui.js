/* [SPB-REV-MATERIAL 2026-10-10] Material tools UI: Material Brush, Spec Brush, Wear Brush, Spec Eyedropper.
 * Tool modes rev-material / rev-spec / rev-wear / rev-specpick (canvasMode). Toolbar menu "Material",
 * keys U (Material Brush) and Shift+U (cycle the four). Probed 2026-10-10 on the live app: U and Shift+U are the only
 * letters with no handler and no side effect (G = Gradient, Shift+N/D/R = zone actions).
 * Controls live in the fixed tool band (#spbToolRowTop); the material swatch + live M/R/CC readout lives in
 * the fixed 45 px options bar (#toolSpecificOptions). A full-res overlay on the SOURCE shows strokes instantly;
 * the LIVE PREVIEW (real engine render) follows after each stroke.
 * Kill switch: window.SPB_REV_MAT_OFF = true or localStorage SPB_REV_MAT_OFF = '1' (checked at boot).
 */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    const M = root.SPBRevMaterial, R = root.SPBRevMatRecipes;
    if (!M || !R || M.off()) return;

    const MODES = { 'rev-material': 'material', 'rev-spec': 'spec', 'rev-wear': 'wear', 'rev-specpick': 'pick' };
    const CYCLE = ['rev-material', 'rev-spec', 'rev-wear', 'rev-specpick'];
    const NAMES = { material: 'Material Brush', spec: 'Spec Brush', wear: 'Wear Brush', pick: 'Spec Eyedropper' };
    const GUIDE = {
        'rev-material': ['Material Brush', (typeof M.bsOff === 'function' && !M.bsOff())
            ? 'Pick any SPB finish (every category, Far Out too), then brush it: Paint + Spec (the whole finish, pattern included), Spec only (your paint stays) or Paint only (your spec stays). The sliders button sets colour, scale, rotation and strength like a zone. Alt erases.   [ U ]'
            : 'Pick any SPB finish in the bar above, then brush it onto the car: real paint + spec, soft edges, stays inside the zone. Keep Colour keeps the paint colour that is already there. Alt erases.   [ U ]'],
        'rev-spec': ['Spec Brush', 'Paints only the spec map (metal / roughness / clearcoat) and keeps your paint. Presets or exact values; switch channels off to leave them alone. Alt erases.   [ Shift+U ]'],
        'rev-wear': ['Wear Brush', 'One stroke writes real race wear, paint and spec together: dirt and grime, rubber marks, stone chips. Stroke the way the air flows. Alt erases.   [ Shift+U ]'],
        'rev-specpick': ['Spec Eyedropper', 'Click the car to pick its paint + spec at that pixel, then brush with it.   [ Shift+U ]']
    };

    // ---------------------------------------------------------------- settings (per viewer)
    const LS = 'spbRevMat.v1';
    const T = { finishId: 'chrome', keep: false, presetId: 'gloss', custom: { m: 0, r: 30, cc: 16 }, chan: [1, 1, 1], grain: 0, wearType: 'dirt', picked: null, pickPaint: true,
        mode: null, params: null, specFinish: 'fo_mirror_ball' };   // [BRUSH-STUDIO 2026-10-10] mode / slider params / the Spec Brush's "from any finish" source
    try { const s = JSON.parse(root.localStorage.getItem(LS) || 'null'); if (s && typeof s === 'object') Object.keys(T).forEach(function (k) { if (s[k] !== undefined && k !== 'picked') T[k] = s[k]; }); } catch (_) {}
    function save() { try { const c = Object.assign({}, T); delete c.picked; root.localStorage.setItem(LS, JSON.stringify(c)); } catch (_) {} }
    // [BRUSH-STUDIO 2026-10-10] one brush, three modes. Keep Colour == "Spec only" (an older saved keep:true opens in Spec only).
    const STUDIO = typeof M.bsOff === 'function' && !M.bsOff();
    if (T.mode !== 'both' && T.mode !== 'spec' && T.mode !== 'paint') T.mode = T.keep ? 'spec' : 'both';
    // [BRUSH-STUDIO 2026-10-10] Spec only leaves the paint byte-identical; "Surface texture" (the T-2 Keep Colour texture) is opt-in.
    // A saved Keep Colour (keep:true from before the studio) comes back as Spec only WITH the texture, i.e. the look it had.
    if (typeof T.texture !== 'boolean') T.texture = !!T.keep;
    T.params = M.normParams ? M.normParams(T.params) : T.params;
    function studioOn() { return STUDIO && !(M.bsOff && M.bsOff()); }
    function setStudioMode(md) { T.mode = md === 'spec' || md === 'paint' ? md : 'both'; T.keep = T.mode === 'spec'; save(); }
    // the params a stroke carries: a setting that cannot show in this mode is left at its default (no extra engine render for nothing)
    function strokeParams(md) {
        const p = M.normParams(T.params);
        if (md === 'spec') { p.color = null; p.colorStrength = 1; }
        if (md === 'paint') p.specStrength = 1;
        return p;
    }

    // [PERF-4 2026-10-10] (lane PERF-4, item 2) ask the server to render + memoise this coat's finish on the full canvas NOW (Apply in the picker, pointer-down of a
    // stroke) so the first stroke of a slow finish finds it ready instead of paying it inside its own preview. Fire and forget, idle-only on the server, a no-op
    // without a live preview source. Kill switch: window.SPB_PERF4_OFF / localStorage SPB_PERF4_OFF=1 / env SPB_PERF4_OFF. Proof: _easy_claude_work/perf4/PROGRESS.md.
    let lastWarmKey = '';
    function warmFor(finishId, md) {
        try {
            const P4 = root.SPBPerf4;
            if (!P4 || !finishId || !studioOn() || typeof M.warmZone !== 'function') return;
            const base = P4.ready();
            if (!base) return;
            const p = strokeParams(md), key = base + '|' + finishId + '|' + M.psig(p);
            if (key === lastWarmKey) return;
            const pack = M.warmZone(finishId, p);
            if (pack && P4.warm(pack)) lastWarmKey = key;
        } catch (_) {}
    }
    function preset() {
        if (T.presetId === 'finish' && studioOn()) return { id: 'finish', name: 'From finish: ' + M.finishName(T.specFinish), m: 0, r: 0, cc: 16, chan: [1, 1, 1], grain: 0 };   // [BRUSH-STUDIO] display only
        if (T.presetId === 'picked' && T.picked) return { id: 'picked', name: 'Picked', m: T.picked.m, r: T.picked.r, cc: T.picked.cc, chan: T.chan.slice(), grain: 0 };
        if (T.presetId === 'raw' || !R.PRESET_BY_ID[T.presetId]) return { id: 'raw', name: 'Custom', m: T.custom.m, r: T.custom.r, cc: T.custom.cc, chan: T.chan.slice(), grain: T.grain || 0 };
        const p = R.PRESET_BY_ID[T.presetId];
        return { id: p.id, name: p.name, m: p.m, r: p.r, cc: p.cc, chan: T.chan.slice(), grain: T.grain, grainKind: p.grainKind };
    }
    function setPreset(id) {
        // accept a preset id, its display name or a loose alias ('brushed_metal', 'Brushed Metal' -> 'brushed')
        if (id && id !== 'picked' && !R.PRESET_BY_ID[id]) {
            const k = String(id).toLowerCase().replace(/[^a-z]/g, '');
            const hit = R.PRESETS.find(function (p) { const n = p.name.toLowerCase().replace(/[^a-z]/g, ''); return n === k || p.id === k || k.indexOf(p.id) === 0; });
            if (hit) id = hit.id;
        }
        if (id === 'finish' && !studioOn()) id = 'gloss';
        T.presetId = id;
        const p = R.PRESET_BY_ID[id];
        if (p && id !== 'raw') { T.chan = p.chan.slice(); T.grain = p.grain; }
        if (id === 'picked') { T.chan = [1, 1, 1]; T.grain = 0; }
        save(); buildBand(); updateBar();
    }

    function mode() { try { return String(root.canvasMode || (typeof canvasMode !== 'undefined' ? canvasMode : '') || ''); } catch (_) { return ''; } }
    function tool() { return MODES[mode()] || null; }
    function setMode(m) { if (typeof root.setCanvasMode === 'function') root.setCanvasMode(m); sync(true); }
    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (_) {} }
    // [TICKETS-3 2026-10-10 item 4] kill switch: window.SPB_T3_OFF or SPB_T3_4_OFF
    function t3off(n) { try { return !!(root.SPB_T3_OFF || root['SPB_T3_' + n + '_OFF']); } catch (_) { return false; } }
    function el(tag, attrs, html) {
        const e = doc.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function (k) { if (k === 'style') e.style.cssText = attrs[k]; else if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); });
        if (html != null) e.innerHTML = html;
        return e;
    }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
    function brush() {
        const n = function (id, d) { const e = doc.getElementById(id); const v = e ? Number(e.value) : NaN; return isFinite(v) ? v : d; };
        return { radius: Math.max(1, n('brushSize', 20)), opacity: n('brushOpacity', 100) / 100, hardness: n('brushHardness', 80) / 100 };
    }
    function swatchUrl(id) { try { return typeof root.getSwatchUrl === 'function' ? root.getSwatchUrl(id, '#888888', false) : null; } catch (_) { return null; } }
    function finishSwatchHex(id) {
        const raw = String(id || '').replace(/^mono:/, '');
        try { if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[raw] && BASES_BY_ID[raw].swatch) return BASES_BY_ID[raw].swatch; } catch (_) {}
        try { if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[raw] && MONOLITHICS_BY_ID[raw].swatch) return MONOLITHICS_BY_ID[raw].swatch; } catch (_) {}
        return '#9aa0a8';
    }
    function hexRgb(h) { const m = /^#?([0-9a-f]{6})$/i.exec(String(h || '')); const v = m ? parseInt(m[1], 16) : 0x9aa0a8; return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; }

    // ---------------------------------------------------------------- overlay (instant stroke feedback on SOURCE)
    let ov = null, octx = null, dirty = null, rafId = 0;
    function overlay() {
        const S = M.state, pc = doc.getElementById('paintCanvas');
        if (!pc || !S.W) return null;
        if (!ov || !ov.isConnected) {
            ov = doc.getElementById('spbRevMatOverlay') || el('canvas', { id: 'spbRevMatOverlay', 'aria-hidden': 'true' });
            const rc = doc.getElementById('regionCanvas');
            const host = pc.parentNode;
            if (rc && rc.parentNode === host) host.insertBefore(ov, rc.nextSibling); else host.appendChild(ov);
            octx = null;
        }
        if (ov.width !== S.W || ov.height !== S.H) { ov.width = S.W; ov.height = S.H; octx = null; }
        if (!octx) octx = ov.getContext('2d');
        syncOverlayBox();
        return ov;
    }
    function syncOverlayBox() {
        if (!ov) return;
        const pc = doc.getElementById('paintCanvas');
        const src = doc.getElementById('regionCanvas') || pc;
        if (!src) return;
        const st = ov.style;
        const want = 'position:absolute;pointer-events:none;z-index:3;image-rendering:pixelated;left:' + (src.style.left || '0') + ';top:' + (src.style.top || '0') +
            ';width:' + (src.style.width || (pc.style.width || '')) + ';height:' + (src.style.height || (pc.style.height || '')) + ';transform:' + (src.style.transform || 'none') +
            ';display:' + (tool() ? 'block' : 'none');
        if (st.cssText !== want) st.cssText = want;
    }
    function queue(r) {
        if (!r) return;
        dirty = dirty ? [Math.min(dirty[0], r.x), Math.min(dirty[1], r.y), Math.max(dirty[2], r.x + r.w), Math.max(dirty[3], r.y + r.h)] : [r.x, r.y, r.x + r.w, r.y + r.h];
        if (!rafId) rafId = root.requestAnimationFrame(flush);
    }
    function flush() { rafId = 0; const d = dirty; dirty = null; if (d) drawOverlay(d[0], d[1], d[2], d[3]); }
    function redrawAll() { const S = M.state; if (S.W) drawOverlay(0, 0, S.W, S.H); }
    function drawOverlay(x0, y0, x1, y1) {
        const S = M.state;
        if (!overlay() || x1 <= x0 || y1 <= y0) return;
        const W = S.W, w = x1 - x0, h = y1 - y0, img = octx.createImageData(w, h), d = img.data;
        const coats = S.coats, cols = coats.map(function (c) { return hexRgb(c.params && c.params.color ? c.params.color : finishSwatchHex(c.finishId)); });   // [BRUSH-STUDIO] a colour override shows its colour
        const sv = S.sv, sc = S.sc, pv = S.pv, pcv = S.pc;
        // premultiplied "over" stack: coat (swatch colour + sheen bands) -> spec hatch -> exact paint layer
        for (let y = y0; y < y1; y++) {
            let o = (y - y0) * w * 4;
            for (let x = x0; x < x1; x++, o += 4) {
                const i = y * W + x;
                let r = 0, g = 0, b = 0, a = 0, best = 0, bk = -1;
                for (let k = 0; k < coats.length; k++) { const m = coats[k].mask[i]; if (m > best) { best = m; bk = k; } }
                if (bk >= 0) {
                    const c = cols[bk], sheen = ((x + y) % 40) < 5 ? 1.22 : (((x - y + 4096) % 9) === 0 ? 0.86 : 1), t = best / 255 * 0.9;
                    if (coats[bk].keep) { if (sheen !== 1) { const k = best / 255 * (sheen > 1 ? 0.38 : 0.26), v = sheen > 1 ? 255 : 30; r = v * k; g = v * k; b = v * k; a = k; } }
                    else { r = Math.min(255, c[0] * sheen) * t; g = Math.min(255, c[1] * sheen) * t; b = Math.min(255, c[2] * sheen) * t; a = t; }
                }
                if (sc) {
                    const sa = Math.max(sc[i * 3], sc[i * 3 + 1], sc[i * 3 + 2]);
                    if (sa && ((x + y) & 7) === 0) { const t = sa / 255 * 0.55; r = r * (1 - t) + 235 * t; g = g * (1 - t) + 240 * t; b = b * (1 - t) + 245 * t; a = a * (1 - t) + t; }
                    const pa = pcv[i];
                    if (pa) { const t = pa / 255; r = r * (1 - t) + pv[i * 3] * t; g = g * (1 - t) + pv[i * 3 + 1] * t; b = b * (1 - t) + pv[i * 3 + 2] * t; a = a * (1 - t) + t; }
                }
                if (a > 0.002) { d[o] = Math.min(255, r / a); d[o + 1] = Math.min(255, g / a); d[o + 2] = Math.min(255, b / a); d[o + 3] = Math.round(a * 255); }
            }
        }
        octx.putImageData(img, x0, y0);
    }

    // ---------------------------------------------------------------- brush cursor ring
    let ring = null;
    function showRing(e) {
        const t = tool(), pc = doc.getElementById('paintCanvas');
        if (!t || t === 'pick' || !pc) { if (ring) ring.style.display = 'none'; return; }
        if (!ring) { ring = el('div', { id: 'spbRevMatRing', 'aria-hidden': 'true' }); doc.body.appendChild(ring); }
        const rect = pc.getBoundingClientRect(), s = rect.width / pc.width, rad = Math.max(2, brush().radius * s);
        ring.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483000;border-radius:50%;border:1px solid rgba(255,255,255,.95);box-shadow:0 0 0 1px rgba(0,0,0,.55);' +
            'left:' + (e.clientX - rad) + 'px;top:' + (e.clientY - rad) + 'px;width:' + (rad * 2) + 'px;height:' + (rad * 2) + 'px;display:block';
    }
    function hideRing() { if (ring) ring.style.display = 'none'; }

    // ---------------------------------------------------------------- pointer routing
    let spaceHeld = false, drag = null, pickGuardUntil = 0;
    root.addEventListener('keydown', function (e) { if (e.code === 'Space') spaceHeld = true; }, true);
    root.addEventListener('keyup', function (e) { if (e.code === 'Space') spaceHeld = false; }, true);
    root.addEventListener('blur', function () { spaceHeld = false; });

    function docPt(e) {
        const pc = doc.getElementById('paintCanvas');
        const rect = pc.getBoundingClientRect();
        return { x: (e.clientX - rect.left) * pc.width / rect.width - 0.5, y: (e.clientY - rect.top) * pc.height / rect.height - 0.5 };
    }
    function strokeOpts(t, erase) {
        const b = brush();
        const o = { tool: t, erase: !!erase, opacity: b.opacity, hardness: b.hardness };
        if (t === 'material') {
            o.finishId = T.finishId; o.keep = !!T.keep;
            // [BRUSH-STUDIO 2026-10-10] the mode + the zone sliders ride on the stroke (Alt erases only the planes of the mode)
            if (studioOn()) { o.studio = true; o.mode = T.mode; o.params = strokeParams(T.mode); o.keep = T.mode === 'spec' && !!T.texture; }
        }
        if (t === 'spec' && T.presetId === 'finish' && studioOn() && T.specFinish) {
            // [BRUSH-STUDIO 2026-10-10] Spec Brush, source "any finish": a Spec only coat of that finish (its spec + pattern structure; paint stays)
            o.tool = 'material'; o.studio = true; o.mode = 'spec'; o.keep = !!T.texture; o.finishId = T.specFinish; o.params = strokeParams('spec');
            return o;
        }
        if (t === 'spec') { o.preset = preset(); o.paint = (T.presetId === 'picked' && T.picked && T.pickPaint) ? T.picked.paint : null; }
        if (t === 'wear') o.wearType = T.wearType;
        return o;
    }
    function onDown(e) {
        const t = tool();
        if (!t || e.button !== 0 || spaceHeld || e.ctrlKey || e.metaKey) return;
        const pc = doc.getElementById('paintCanvas');
        const tgt = e.target;
        const onCanvas = tgt === pc || (tgt && tgt.id === 'spbRevMatOverlay');
        const pimg = doc.getElementById('livePreviewImg');
        const onPreview = t === 'pick' && pimg && tgt === pimg;
        if (!onCanvas && !onPreview) return;
        e.preventDefault(); e.stopImmediatePropagation();
        if (t === 'pick') { pickGuardUntil = performance.now() + 1200; pickAt(e, onPreview ? pimg : pc); return; }
        if (!M.beginStroke(strokeOpts(t, e.altKey))) { toast('Material tools need a loaded car paint first.', true); return; }
        if (!e.altKey) { if (t === 'material') warmFor(T.finishId, T.mode); else if (t === 'spec' && T.presetId === 'finish' && T.specFinish) warmFor(T.specFinish, 'spec'); }   // [PERF-4 2026-10-10]
        const p = docPt(e);
        drag = { first: p, last: p, pressure: e.pointerType === 'pen' ? (e.pressure || 0.5) : 1, id: e.pointerId, erase: !!e.altKey };
        stamp(p, drag.pressure);
        root.addEventListener('pointermove', onMove, true);
        root.addEventListener('pointerup', onUp, true);
        root.addEventListener('pointercancel', onUp, true);
    }
    function stamp(p, pr) {
        const b = brush();
        const r = b.radius * (pr < 1 ? (0.35 + 0.65 * pr) : 1);
        M.dab(p.x, p.y, r); // the core emits 'dab' with the touched rect -> overlay
    }
    function onMove(e) {
        if (!drag) return;
        e.preventDefault(); e.stopImmediatePropagation();
        const evs = (typeof e.getCoalescedEvents === 'function' && e.getCoalescedEvents().length) ? e.getCoalescedEvents() : [e];
        const step = Math.max(0.75, brush().radius * 0.18);
        evs.forEach(function (ev) {
            const p = docPt(ev), pr = ev.pointerType === 'pen' ? (ev.pressure || 0.5) : 1;
            const dx = p.x - drag.last.x, dy = p.y - drag.last.y, dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < step) return;
            const n = Math.floor(dist / step);
            for (let k = 1; k <= n; k++) stamp({ x: drag.last.x + dx * k / n, y: drag.last.y + dy * k / n }, pr);
            drag.last = p;
        });
        showRing(e);
    }
    // [SPECIAL-ZONE 2026-10-11 owner] the 0 px toast used to blame "the paintable area" whatever the real reason was. Name it:
    // the active selection, the selected zone's Clip-to-Zone area, a drawn zone region, or (last) the car itself. Kill switch SPB_CLIPTOAST_OFF.
    function missReason(pt) {
        if (root.SPB_CLIPTOAST_OFF) return 'Nothing to paint there: that spot is outside the paintable area';
        try {
            const pc = doc.getElementById('paintCanvas');
            const W = pc && pc.width, H = pc && pc.height;
            const x = pt ? Math.max(0, Math.min(W - 1, Math.floor(pt.x))) : -1, y = pt ? Math.max(0, Math.min(H - 1, Math.floor(pt.y))) : -1;
            if (W && H && x >= 0) {
                const i = y * W + x;
                const z = (typeof zones !== 'undefined') ? zones[selectedZoneIndex] : null;
                const zn = (z && z.name) || 'this zone';
                const raw = (typeof root._activeSelectionMask === 'function') ? root._activeSelectionMask(W, H, false) : null;
                if (raw && raw.length === W * H && !raw[i]) {
                    return (z && z.useRegion && z.regionMask === raw) ? 'Nothing painted: that spot is outside the drawn region of ' + zn : 'Nothing painted: that spot is outside your selection (Ctrl+D clears it)';
                }
                const zc = root.SPBZoneClip;
                if (zc && !root.SPB_ZONECLIP_OFF && z && zc.enabledFor(z)) {
                    const m = zc.clipFor(z, W, H);
                    if (m && m.length === W * H && !m[i]) return 'Nothing painted: that spot is outside ' + zn + ' (Clip to Zone is on; untick it to paint anywhere)';
                }
                return 'Nothing painted: that spot is not on the car';
            }
        } catch (_) {}
        return 'Nothing painted there';
    }
    function onUp(e) {
        if (!drag) return;
        if (e) { e.preventDefault(); e.stopImmediatePropagation(); }
        const wasErase = !!drag.erase;
        const firstPt = drag.first;
        drag = null;
        root.removeEventListener('pointermove', onMove, true);
        root.removeEventListener('pointerup', onUp, true);
        root.removeEventListener('pointercancel', onUp, true);
        // [TICKETS-3 2026-10-10 item 4] IQ3-8: a stroke that added 0 px (every dab fell outside the paintable area) records no undo step (core endStroke returns null for it)
        // and used to end in silence; say so in one line. An Alt erase over nothing is not a paint miss, and a cancelled stroke (no live stroke) is not either.
        const live = !!(M.state && M.state.st);
        const entry = M.endStroke();
        if (!entry && live && !wasErase && !t3off(4)) toast(missReason(firstPt));
        if (dirty) flush();
    }
    root.addEventListener('pointerdown', onDown, true);
    // the app's own mouse path must never see a stroke that belongs to these tools
    ['mousedown', 'mouseup', 'click', 'dblclick'].forEach(function (type) {
        root.addEventListener(type, function (e) {
            const tgt = e.target;
            // the pick switches tools before the click lands: never let that click open the preview lightbox
            if (tgt && tgt.id === 'livePreviewImg' && performance.now() < pickGuardUntil) { e.preventDefault(); e.stopImmediatePropagation(); return; }
            const t = tool(); if (!t || e.button !== 0 || spaceHeld) return;
            if (tgt && (tgt.id === 'paintCanvas' || tgt.id === 'spbRevMatOverlay' || (t === 'pick' && tgt.id === 'livePreviewImg'))) { e.preventDefault(); e.stopImmediatePropagation(); }
        }, true);
    });
    root.addEventListener('pointermove', function (e) {
        if (drag) return;
        const t = tool(); if (!t) { hideRing(); return; }
        const tgt = e.target;
        if (tgt && (tgt.id === 'paintCanvas' || tgt.id === 'spbRevMatOverlay')) showRing(e); else hideRing();
    }, { passive: true });

    // ---------------------------------------------------------------- Spec Eyedropper
    const _paintCache = { src: '', data: null, w: 0, h: 0 };
    function previewPaintData() {
        const img = doc.getElementById('livePreviewImg');
        if (!img || !img.complete || !img.naturalWidth) return null;
        const src = img.currentSrc || img.src;
        if (_paintCache.src === src && _paintCache.data) return _paintCache;
        try {
            const cv = doc.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight;
            const cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(img, 0, 0);
            _paintCache.src = src; _paintCache.w = cv.width; _paintCache.h = cv.height; _paintCache.data = cx.getImageData(0, 0, cv.width, cv.height).data;
            return _paintCache;
        } catch (_) { return null; }
    }
    function specImageSrc() { const s = doc.getElementById('livePreviewSpecImg'); return s && (s.currentSrc || s.src) || ''; }
    function pickAt(e, srcEl) {
        const rect = srcEl.getBoundingClientRect();
        const fx = (e.clientX - rect.left) / rect.width, fy = (e.clientY - rect.top) / rect.height;
        if (fx < 0 || fy < 0 || fx >= 1 || fy >= 1) return;
        const S = M.state; M.ensure();
        const dx = Math.floor(fx * S.W), dy = Math.floor(fy * S.H);
        const pd = previewPaintData();
        const src = specImageSrc();
        if (!pd || !src || !root.SPBSpecPngPixels) {
            // the preview may be mid-refresh: pick as soon as it has loaded (once), otherwise say why
            const img = doc.getElementById('livePreviewImg');
            if (img && !e.__spbRetry && img.src && !img.complete) {
                const ev = { clientX: e.clientX, clientY: e.clientY, __spbRetry: true };
                img.addEventListener('load', function () { setTimeout(function () { pickAt(ev, srcEl); }, 60); }, { once: true });
                return;
            }
            toast('Spec Eyedropper reads the LIVE PREVIEW. Wait for it to render, then click again.', true); return;
        }
        root.SPBSpecPngPixels.load(src).then(function (sp) {
            const sx = Math.min(sp.width - 1, Math.floor(fx * sp.width)), sy = Math.min(sp.height - 1, Math.floor(fy * sp.height));
            const k = (sy * sp.width + sx) * 4;
            const px = Math.min(pd.w - 1, Math.floor(fx * pd.w)), py = Math.min(pd.h - 1, Math.floor(fy * pd.h)), q = (py * pd.w + px) * 4;
            const pick = { m: sp.data[k], r: sp.data[k + 1], cc: sp.data[k + 2], a: sp.data[k + 3], paint: [pd.data[q], pd.data[q + 1], pd.data[q + 2]], at: [dx, dy] };
            const near = R.nearestPreset(pick.m, pick.r, pick.cc);
            pick.near = near ? near.name : '';
            T.picked = pick;
            const here = M.sampleAt(dx, dy);
            const coat = here && here.coats.length ? here.coats.sort(function (a, b) { return b.a - a.a; })[0] : null;
            if (coat && coat.a >= 128) {
                T.finishId = coat.finishId; T.keep = !!coat.keep;
                if (coat.plane && studioOn()) {
                    // [BRUSH-STUDIO 2026-10-10] load the finish, its mode and its sliders
                    const same = function (x) { return x.finishId === coat.finishId && M.psig(x.params) === M.psig(coat.params); };
                    let md = coat.plane === 'spec' && coat.keep ? 'spec' : coat.plane;
                    if (!coat.keep && here.coats.some(function (x) { return x.plane && x.plane !== coat.plane && !x.keep && same(x); })) md = 'both';
                    if (md === 'spec') T.texture = !!coat.keep;
                    setStudioMode(md); T.params = M.normParams(coat.params);
                } else if (studioOn()) setStudioMode(coat.keep ? 'spec' : 'both');
                save();
                setMode('rev-material');
                toast('Picked ' + coat.name + ' (M ' + pick.m + ' · R ' + pick.r + ' · CC ' + pick.cc + '). Material Brush is loaded with it.');
            } else {
                T.presetId = 'picked'; T.chan = [1, 1, 1]; T.grain = 0; save();
                setMode('rev-spec');
                toast('Picked M ' + pick.m + ' · R ' + pick.r + ' · CC ' + pick.cc + (pick.near ? ' (reads as ' + pick.near + ')' : '') + ' + its paint. Spec Brush is loaded with it.');
            }
            root.__spbRevMatLastPick = pick;
        }).catch(function () { toast('Could not read the live spec map. Render the preview once, then try again.', true); });
    }

    // ---------------------------------------------------------------- finish picker (the app's own)
    let finishBtn = null, specFinBtn = null;
    function openPicker(btn) {
        if (typeof root.openSwatchPicker !== 'function') return;
        let zi = 0;
        try { zi = (typeof selectedZoneIndex === 'number' && zones[selectedZoneIndex]) ? selectedZoneIndex : 0; } catch (_) {}
        // [BRUSH-STUDIO 2026-10-10] openSwatchPicker TOGGLES when a 'base' picker is already open for the same zone,
        // so a picker left open by the other brush (or a zone) would just close. Close it first, then open for this button.
        try { if (typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.open && swatchPopupState.triggerEl !== btn && typeof root.closeSwatchPicker === 'function') root.closeSwatchPicker(); } catch (_) {}
        root.openSwatchPicker(btn, 'base', zi);
    }
    function wrapPicker() {
        const cur = root.selectSwatchItem;
        if (typeof cur !== 'function' || cur.__spbRevMat) return;
        const w = function (id) {
            try {
                // [BRUSH-STUDIO 2026-10-10] the Spec Brush's "from any finish" button opens the same picker
                if (specFinBtn && typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.open && swatchPopupState.triggerEl === specFinBtn) {
                    if (id && id !== 'none' && id !== 'dualshift_custom') {
                        T.specFinish = String(id); T.presetId = 'finish'; save();
                        warmFor(T.specFinish, 'spec');   // [PERF-4 2026-10-10]
                        if (typeof _spbBumpFinishUsage === 'function') _spbBumpFinishUsage(id);
                    }
                    if (typeof root.closeSwatchPicker === 'function') root.closeSwatchPicker();
                    buildBand(); updateBar();
                    if (tool() !== 'spec') setMode('rev-spec');
                    return;
                }
                if (finishBtn && typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.open && swatchPopupState.triggerEl === finishBtn) {
                    if (id && id !== 'none' && id !== 'dualshift_custom') {
                        T.finishId = String(id); save();
                        warmFor(T.finishId, T.mode);   // [PERF-4 2026-10-10]
                        if (typeof _spbBumpFinishUsage === 'function') _spbBumpFinishUsage(id);
                    }
                    if (typeof root.closeSwatchPicker === 'function') root.closeSwatchPicker();
                    buildBand(); updateBar();
                    if (tool() !== 'material') setMode('rev-material');
                    return;
                }
            } catch (e) { console.warn('[REV-MATERIAL] picker', e); }
            return cur.apply(this, arguments);
        };
        w.__spbRevMat = true;
        root.selectSwatchItem = w;
    }

    // ---------------------------------------------------------------- tool band (fixed 40 px) + options bar (fixed 45 px)
    let band = null, bar = null, builtFor = '';
    let tight = false, popOpen = false, fitting = false, fitSig = '';   // [REV-MATERIAL-2] tier 3 (only when the row would scroll): swatch-only finish, Spec values in a popover
    const BRUSH_IDS = ['brushSizeLabel', 'brushSize', 'brushSizeVal', 'brushOpacityLabel', 'brushOpacity', 'brushOpacityVal', 'brushHardnessLabel', 'brushHardness', 'brushHardnessVal'];
    function host() { return doc.getElementById('spbToolRowTop') || doc.getElementById('toolSpecificOptions'); }
    function ensureUi() {
        const h = host();
        if (!h) return false;
        if (!band || band.parentNode !== h) {
            band = band || el('span', { id: 'spbRevMatBand', class: 'spb-rm-band', role: 'group', 'aria-label': 'Material tool options' });
            // first in the row: the finish / preset stay in view when a narrow window makes the row scroll
            h.insertBefore(band, h.firstChild); builtFor = '';
            watchWidth(h);
        }
        const tb = doc.getElementById('toolSpecificOptions');
        if (tb && (!bar || bar.parentNode !== tb)) { bar = bar || el('span', { id: 'spbRevMatBar', class: 'spb-rm-bar', 'aria-live': 'polite' }); tb.appendChild(bar); }
        return true;
    }
    let ro = null;
    function watchWidth(h) {
        fit();
        try { if (ro) ro.disconnect(); ro = new ResizeObserver(fit); ro.observe(h); } catch (_) {}
    }
    // [REV-MATERIAL-2 2026-10-10] width tiers: compact (< 980 px) and tight. Tight is decided by measuring: render the normal band,
    // and only if the row would scroll sideways switch to the tight band (swatch-only finish, Spec values behind one button, the app's size /
    // opacity / hardness sliders without labels). Any window size from 1100 up either fits as is or compacts to fit.
    function setTight(v) {
        if (v === tight) return;
        tight = v; if (!v) popOpen = false;
        if (builtFor === 'spec' || (builtFor === 'material' && studioOn())) buildBand();   // the Spec band has a tight variant (popover); [BRUSH-STUDIO] the mode select has short labels
    }
    function fit() {
        const h = host();
        if (!band || !h || fitting) return;
        fitting = true;
        try {
            band.classList.toggle('spb-rm-compact', h.clientWidth < 980);
            if (tool() && builtFor) {
                const pop = popOpen;   // the measuring pass below must not close an open Spec popover
                setTight(false); hostClass();
                const want = h.scrollWidth > h.clientWidth + 1;
                if (want) popOpen = pop;
                setTight(want);
            } else setTight(false);
            hostClass(); positionPop();
            fitSig = h.clientWidth + '|' + h.scrollWidth + '|' + builtFor + '|' + tight;
        } finally { fitting = false; }
    }
    function fitCheck() {   // cheap: re-measures only when the row's width or content width changed (a zone gained an area, the app swapped its groups...)
        const h = host();
        if (!h || !band || !tool() || fitting) return;
        if ((h.clientWidth + '|' + h.scrollWidth + '|' + builtFor + '|' + tight) !== fitSig) fit();
    }
    // [REV-MATERIAL-2 2026-10-10] tight tier: the host row gets a class so the app's own brush sliders compact too (CSS only, scoped to the four tools)
    function hostClass() {
        const h = host();
        if (h) h.classList.toggle('spb-rm-tight', !!(tight && tool()));
        band && band.classList.toggle('spb-rm-tight', tight);
    }
    function positionPop() {
        [['spbRevMatMore', 'spbRevMatPop'], ['spbRevMatAdjBtn', 'spbRevMatAdj']].forEach(function (ids) {   // [BRUSH-STUDIO] + the slider popover
            const b = doc.getElementById(ids[0]), p = doc.getElementById(ids[1]);
            if (!b || !p || p.hasAttribute('hidden')) return;
            const r = b.getBoundingClientRect(), pw = p.offsetWidth || 280;
            p.style.left = Math.max(6, Math.min(r.left, (root.innerWidth || 1100) - pw - 6)) + 'px';
            p.style.top = Math.round(r.bottom + 6) + 'px';
        });
    }
    function closePop() { if (!popOpen) return; popOpen = false; if (builtFor) buildBand(); }
    doc.addEventListener('pointerdown', function (e) {
        const t = e.target;
        if (adjOpen && !(t && t.closest && (t.closest('#spbRevMatAdj') || t.closest('#spbRevMatAdjBtn')))) closeAdj();   // [BRUSH-STUDIO]
        if (!popOpen) return;
        if (t && t.closest && (t.closest('#spbRevMatPop') || t.closest('#spbRevMatMore'))) return;
        closePop();
    }, true);
    doc.addEventListener('keydown', function (e) {
        if (adjOpen && e.key === 'Escape') { closeAdj(); const b = doc.getElementById('spbRevMatAdjBtn'); if (b) b.focus(); return; }
        if (popOpen && e.key === 'Escape') { const m = doc.getElementById('spbRevMatMore'); closePop(); if (m && doc.getElementById('spbRevMatMore')) doc.getElementById('spbRevMatMore').focus(); }
    }, true);
    function chip(label, ch, val, title) {
        const on = T.chan[ch];
        return '<span class="spb-rm-ch' + (on ? '' : ' off') + '" data-ch="' + ch + '"><button type="button" class="spb-rm-chbtn" data-ch="' + ch + '" title="' + esc(title) + ' — click to ' + (on ? 'leave this channel alone' : 'paint this channel') + '" aria-pressed="' + (on ? 'true' : 'false') + '">' + label + '</button>' +
            '<input type="number" class="spb-rm-num" data-ch="' + ch + '" min="0" max="255" step="1" value="' + val + '" aria-label="' + esc(title) + ' 0 to 255"></span>';
    }
    // [REV-MATERIAL-2 2026-10-10] Keep Colour: the stroke gets the finish's spec + fine surface texture, the colour already on the car stays
    function keepHtml() {
        return '<label class="spb-rm-clip spb-rm-keep" title="Keep Colour: the stroke gets this finish\'s spec (metal, roughness, clearcoat) and its fine surface texture, but the paint colour already on the car stays. Untick and the finish repaints the colour too."><input type="checkbox" id="spbRevMatKeep"' + (T.keep ? ' checked' : '') + '><span class="spb-rm-cliptx">Keep Colour</span><span class="spb-rm-cliptx-s">Keep</span></label>';
    }
    // [BRUSH-STUDIO 2026-10-10] one brush, three modes + the zone sliders (popover: the 30 px band has no room for five sliders)
    let adjOpen = false;
    const MODE_TIP = 'Paint + Spec: the whole finish, its pattern included. Spec only: the finish\'s spec and pattern structure, your paint stays exactly as it is (Finish sliders > Surface texture adds the finish\'s fine texture to it, the old Keep Colour). Paint only: the finish\'s colour and pattern, your spec stays.';
    function modeHtml() {
        const L = tight ? { both: 'Paint+Spec', spec: 'Spec', paint: 'Paint' } : { both: 'Paint + Spec', spec: 'Spec only', paint: 'Paint only' };
        return '<select id="spbRevMatMode" class="spb-rm-sel spb-rm-mode" aria-label="What the brush paints" title="' + esc(MODE_TIP) + '">' +
            ['both', 'spec', 'paint'].map(function (m) { return '<option value="' + m + '"' + (T.mode === m ? ' selected' : '') + '>' + L[m] + '</option>'; }).join('') + '</select>';
    }
    function presetSelectHtml(p) {
        let h = '<select id="spbRevMatPreset" class="spb-rm-sel" aria-label="Spec preset" title="Spec preset (values from the SPB finish registry), or the spec of any finish">';
        R.PRESETS.forEach(function (q) { h += '<option value="' + q.id + '"' + (q.id === p.id ? ' selected' : '') + '>' + esc(q.name) + '</option>'; });
        if (T.picked) h += '<option value="picked"' + (p.id === 'picked' ? ' selected' : '') + '>Picked</option>';
        if (studioOn()) h += '<option value="finish"' + (p.id === 'finish' ? ' selected' : '') + '>Any finish…</option>';
        if (studioOn() && root.SpbFlakeStudio && !root.SpbFlakeStudio.off()) h += '<option value="flake">Flake Studio…</option>';   // [SPB-REV-FLAKE 2026-10-10] opens Flake Studio aimed at the brush
        return h + '</select>';
    }
    function scaleToPos(s) { return typeof root.spbScaleToSliderPos === 'function' ? root.spbScaleToSliderPos(s) : Math.round(Math.max(0.05, Math.min(5, s)) * 100); }
    function posToScale(v) { return typeof root.spbSliderPosToScale === 'function' ? root.spbSliderPosToScale(v) : (Number(v) || 100) / 100; }
    function adjRow(id, label, min, max, step, val, txt, dis, title) {
        return '<div class="spb-rm-adjrow' + (dis ? ' dis' : '') + '" title="' + esc(title) + '"><span class="spb-rm-adjl">' + label + '</span><input type="range" id="' + id + '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + val + '"' + (dis ? ' disabled' : '') + ' aria-label="' + esc(label) + '"><span class="spb-rm-adjv" id="' + id + 'V">' + txt + '</span></div>';
    }
    function adjHtml(md) {
        const p = M.normParams(T.params), set = !M.isDefaultParams(strokeParams(md)) || (md === 'spec' && !!T.texture);
        const noCol = md === 'spec', noSpec = md === 'paint';
        let h = '<button type="button" class="spb-rm-more spb-rm-adjbtn' + (adjOpen ? ' on' : '') + (set ? ' set' : '') + '" id="spbRevMatAdjBtn" aria-haspopup="true" aria-expanded="' + (adjOpen ? 'true' : 'false') + '" aria-controls="spbRevMatAdj" title="Finish sliders (the same as a zone\'s): colour, scale, rotation, strength, spec strength' + (set ? ' · now: ' + esc(M.paramsLabel(strokeParams(md))) : '') + '">' +
            '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2v10M7 2v10M11 2v10" stroke="currentColor" stroke-width="1.2" fill="none" stroke-linecap="round" opacity=".55"/><rect x="1.5" y="7.5" width="3" height="2.4" rx=".6" fill="currentColor"/><rect x="5.5" y="3.5" width="3" height="2.4" rx=".6" fill="currentColor"/><rect x="9.5" y="9" width="3" height="2.4" rx=".6" fill="currentColor"/></svg></button>';
        h += '<div class="spb-rm-pop spb-rm-adj" id="spbRevMatAdj" role="group" aria-label="Brush finish sliders"' + (adjOpen ? '' : ' hidden') + '>' +
            // [BRUSH-STUDIO 2026-10-10] colour: Tint = the zone's COLOR LAB Depth (keeps the finish's pattern), Solid = Use solid color + Color Strength
            '<div class="spb-rm-adjrow' + (noCol ? ' dis' : '') + '" title="' + (noCol ? 'Spec only keeps your paint colour' : 'Colour the finish (a zone\'s base colour): Tint keeps its pattern, Solid paints one flat colour') + '"><label class="spb-rm-adjl"><input type="checkbox" id="spbRevMatColOn"' + (p.color ? ' checked' : '') + (noCol ? ' disabled' : '') + '> Colour</label>' +
            '<input type="color" id="spbRevMatCol" value="' + esc(p.color || T.lastColor || '#d42a2a') + '"' + (noCol ? ' disabled' : '') + ' aria-label="Colour">' +
            '<select id="spbRevMatColMode" class="spb-rm-colmode" aria-label="How the colour goes on" title="Tint recolours the finish and keeps its pattern. Solid lays one flat colour under the finish (like Use solid color on a zone)."' + (noCol || !p.color ? ' disabled' : '') + '><option value="tint"' + (p.colorMode === 'tint' ? ' selected' : '') + '>Tint</option><option value="solid"' + (p.colorMode === 'solid' ? ' selected' : '') + '>Solid</option></select></div>' +   // [BRUSH-STUDIO 2026-10-10] short labels: the long ones were cut off at 1100 px (tooltip explains)
            '<div class="spb-rm-adjrow' + (noCol || !p.color ? ' dis' : '') + '" id="spbRevMatColStrRow" title="' + (p.colorMode === 'tint' ? 'Tint depth (a zone\'s Color Lab Depth): more = deeper colour, the pattern stays' : 'Colour strength (a zone\'s Color Strength)') + '"><span class="spb-rm-adjl" id="spbRevMatColStrL">' + (p.colorMode === 'tint' ? 'Tint depth' : 'Colour strength') + '</span>' +
            '<input type="range" id="spbRevMatColStr" min="0" max="100" step="1" value="' + Math.round((p.colorMode === 'tint' ? p.colorDepth : p.colorStrength) * 100) + '"' + (noCol || !p.color ? ' disabled' : '') + ' aria-label="Colour depth or strength"><span class="spb-rm-adjv" id="spbRevMatColStrV">' + Math.round((p.colorMode === 'tint' ? p.colorDepth : p.colorStrength) * 100) + '%</span></div>' +
            adjRow('spbRevMatScale', 'Scale', 0, 1000, 1, scaleToPos(p.scale), p.scale.toFixed(2) + 'x', false, 'Base scale: the size of the finish\'s pattern (a zone\'s Base Scale)') +
            adjRow('spbRevMatRot', 'Rotation', 0, 355, 5, p.rotation, p.rotation + '°', false, 'Base rotation (a zone\'s Base Rotation)') +
            adjRow('spbRevMatStr', 'Strength', 0, 200, 5, Math.round(p.strength * 100), Math.round(p.strength * 100) + '%', false, 'Base strength (a zone\'s Strength)') +
            adjRow('spbRevMatSpecStr', 'Spec strength', 0, 200, 5, Math.round(p.specStrength * 100), Math.round(p.specStrength * 100) + '%', noSpec, noSpec ? 'Paint only keeps your spec' : 'Spec strength (a zone\'s Spec Strength)') +
            // [BRUSH-STUDIO 2026-10-10] Spec only: opt-in T-2 Keep Colour texture (off = the paint stays byte-identical)
            (md === 'spec' ? '<div class="spb-rm-adjrow" title="Off: your paint stays exactly as it is. On: the finish\'s fine light / dark surface texture is added to your paint, its colour stays (the old Keep Colour)."><label class="spb-rm-adjl spb-rm-adjwide"><input type="checkbox" id="spbRevMatTex"' + (T.texture ? ' checked' : '') + '> Surface texture on my paint</label></div>' : '') +
            // [SPB-REV-FLAKE 2026-10-10] the brush carries a Flake Studio recipe: show it, Edit opens Flake Studio, Off drops it (Reset drops it too)
            (p.flake ? '<div class="spb-rm-adjrow" title="This brush lays Flake Studio flake (sized for this car, checked at iRacing distance)"><span class="spb-rm-adjl">Flake</span><span class="spb-rm-adjv" style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(String(p.flake.look || 'custom').replace(/_/g, ' ') + ' ' + (p.flake.size_cm || '') + ' cm') + '</span><button type="button" id="spbRevMatFlakeEdit" title="Open Flake Studio">Edit</button><button type="button" id="spbRevMatFlakeOff" title="Brush without the flake">Off</button></div>' : '') +
            '<div class="spb-rm-adjrow spb-rm-adjfoot"><span class="spb-rm-adjnote">Your next stroke uses these.</span><button type="button" id="spbRevMatAdjReset" title="Back to the finish as it is (colour off, 1.00x, 0°, 100%, 100%)">Reset</button></div></div>';
        return h;
    }
    function adjSet() {   // live label + button state while a slider moves (no band rebuild: it would drop the drag)
        const q = function (id) { return doc.getElementById(id); };
        const md = builtFor === 'spec' ? 'spec' : T.mode, p = M.normParams(T.params);
        const tx = function (id, s) { const e = q(id); if (e) e.textContent = s; };
        tx('spbRevMatScaleV', p.scale.toFixed(2) + 'x'); tx('spbRevMatRotV', p.rotation + '°'); tx('spbRevMatStrV', Math.round(p.strength * 100) + '%');
        tx('spbRevMatSpecStrV', Math.round(p.specStrength * 100) + '%'); tx('spbRevMatColStrV', Math.round((p.colorMode === 'tint' ? p.colorDepth : p.colorStrength) * 100) + '%');
        const cs = q('spbRevMatColStr'); if (cs) cs.disabled = md === 'spec' || !p.color;
        const cm = q('spbRevMatColMode'); if (cm) cm.disabled = md === 'spec' || !p.color;
        const cr = q('spbRevMatColStrRow'); if (cr) cr.classList.toggle('dis', md === 'spec' || !p.color);
        const b = q('spbRevMatAdjBtn'); if (b) b.classList.toggle('set', !M.isDefaultParams(strokeParams(md)) || (md === 'spec' && !!T.texture));
        updateBar();
    }
    function closeAdj() { if (!adjOpen) return; adjOpen = false; if (builtFor) buildBand(); }
    function clipHtml() {
        const ci = M.clipInfo();
        if (!ci || !ci.can) return '';
        const name = (ci.zone && ci.zone.name) || 'Zone';
        return '<label class="spb-rm-clip" title="Strokes stay inside the selected zone (its colours / layers). Untick to paint anywhere."><input type="checkbox" id="spbRevMatClip"' + (ci.on ? ' checked' : '') + '><span class="spb-rm-cliptx">Clip to ' + esc(name) + '</span><span class="spb-rm-cliptx-s">Clip</span></label>';
    }
    function buildBand() {
        if (!ensureUi()) return;
        const t = tool();
        if (!t) { band.style.display = 'none'; band.innerHTML = ''; builtFor = ''; return; }
        band.style.display = 'inline-flex';
        let h = '';
        if (t === 'material') {
            const url = swatchUrl(T.finishId);
            h += '<button type="button" class="spb-rm-finish" id="spbRevMatFinish" title="Finish: ' + esc(M.finishName(T.finishId)) + ' (click to choose another, the normal finish picker)" aria-label="Finish: ' + esc(M.finishName(T.finishId)) + '" aria-haspopup="dialog">' +
                (url ? '<img alt="" src="' + esc(url) + '">' : '<i style="background:' + esc(finishSwatchHex(T.finishId)) + '"></i>') +
                '<span>' + esc(M.finishName(T.finishId)) + '</span><b aria-hidden="true">▾</b></button>';
            if (studioOn()) h += modeHtml() + adjHtml(T.mode) + clipHtml() + '<span class="spb-rm-tip">Alt erases</span>';
            else h += keepHtml() + clipHtml() + '<span class="spb-rm-tip">Alt erases</span>';
        } else if (t === 'spec' && studioOn() && T.presetId === 'finish') {
            // [BRUSH-STUDIO 2026-10-10] Spec Brush, source "any finish": the finish button + its sliders (exact values do not apply here)
            h += presetSelectHtml(preset());
            const url = swatchUrl(T.specFinish);
            h += '<button type="button" class="spb-rm-finish" id="spbRevMatSpecFin" title="Spec from: ' + esc(M.finishName(T.specFinish)) + ' (click to choose another finish, any category)" aria-label="Spec from finish: ' + esc(M.finishName(T.specFinish)) + '" aria-haspopup="dialog">' +
                (url ? '<img alt="" src="' + esc(url) + '">' : '<i style="background:' + esc(finishSwatchHex(T.specFinish)) + '"></i>') +
                '<span>' + esc(M.finishName(T.specFinish)) + '</span><b aria-hidden="true">▾</b></button>';
            h += adjHtml('spec') + clipHtml();
        } else if (t === 'spec') {
            const p = preset();
            h += presetSelectHtml(p);
            const vals = chip('M', 0, p.m, 'Metallic (R channel)') + chip('R', 1, p.r, 'Roughness (G channel, 0 = mirror)') + chip('CC', 2, p.cc, 'Clearcoat (B channel, 16 = max gloss, 255 = dull)') +
                '<label class="spb-rm-grain" title="Fine grain on top of the flat values (brushed streaks, patina mottling, micro texture)"><span class="spb-rm-graintx">Grain</span> <input type="range" id="spbRevMatGrain" min="0" max="100" value="' + (p.grain || 0) + '"></label>' +
                (p.id === 'picked' ? '<label class="spb-rm-clip" title="Also paint the picked paint colour"><input type="checkbox" id="spbRevMatPickPaint"' + (T.pickPaint ? ' checked' : '') + '> Paint too</label>' : '');
            if (tight) {
                // one button holds the exact values, grain, clip and Clear (the row is only ~370 px wide here)
                h += '<button type="button" class="spb-rm-more' + (popOpen ? ' on' : '') + '" id="spbRevMatMore" aria-haspopup="true" aria-expanded="' + (popOpen ? 'true' : 'false') + '" aria-controls="spbRevMatPop" title="Exact values (metal, roughness, clearcoat), grain, clip">' +
                    '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 4h6M11 4h1M2 10h1M6 10h6" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round"/><circle cx="9.5" cy="4" r="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/><circle cx="4.5" cy="10" r="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/></svg></button>' +
                    '<div class="spb-rm-pop" id="spbRevMatPop" role="group" aria-label="Spec brush values"' + (popOpen ? '' : ' hidden') + '><div class="spb-rm-poprow">' + vals + '</div>' + clipHtml() +
                    '<button type="button" class="spb-rm-clear" id="spbRevMatClear" title="Remove every Material, Spec and Wear stroke (Ctrl+Z brings them back)">Clear all strokes</button></div>';
            } else {
                h += vals + clipHtml();
            }
        } else if (t === 'wear') {
            h += '<select id="spbRevMatWear" class="spb-rm-sel" aria-label="Wear type">';
            R.WEAR.forEach(function (w) { h += '<option value="' + w.id + '"' + (w.id === T.wearType ? ' selected' : '') + '>' + esc(w.name) + '</option>'; });
            h += '</select>';
            const w = R.WEAR.find(function (x) { return x.id === T.wearType; });
            h += clipHtml() + '<span class="spb-rm-tip">' + esc(w ? w.tip : '') + ' · Alt erases</span>';
        } else {
            h += '<span class="spb-rm-tip spb-rm-picktip" title="Click the car (Source or Live Preview) to pick its paint + spec, then brush with it.">Click the car (Source or Live Preview) to pick its paint + spec, then brush with it.</span>';
        }
        if (!(t === 'spec' && tight && !(studioOn() && T.presetId === 'finish'))) h += '<button type="button" class="spb-rm-clear" id="spbRevMatClear" title="Remove every Material, Spec and Wear stroke (Ctrl+Z brings them back)">Clear</button>';
        if (builtFor && builtFor !== t) { popOpen = false; adjOpen = false; }
        band.innerHTML = h;
        builtFor = t;
        wireBand();
        showBrushControls(t !== 'pick');
        hostClass(); positionPop();
        if (!fitting) fit();
    }
    function wireBand() {
        const q = function (id) { return doc.getElementById(id); };
        if (q('spbRevMatFinish')) { finishBtn = q('spbRevMatFinish'); finishBtn.addEventListener('click', function () { openPicker(finishBtn); }); }
        if (q('spbRevMatMore')) q('spbRevMatMore').addEventListener('click', function () { popOpen = !popOpen; buildBand(); if (q('spbRevMatMore')) q('spbRevMatMore').focus(); });
        if (q('spbRevMatKeep')) q('spbRevMatKeep').addEventListener('change', function (e) { T.keep = !!e.target.checked; save(); updateBar(); });
        // [BRUSH-STUDIO 2026-10-10] mode, Spec Brush finish source, the slider popover
        if (q('spbRevMatMode')) q('spbRevMatMode').addEventListener('change', function (e) { setStudioMode(e.target.value); buildBand(); updateBar(); });
        if (q('spbRevMatSpecFin')) { specFinBtn = q('spbRevMatSpecFin'); specFinBtn.addEventListener('click', function () { openPicker(specFinBtn); }); }
        if (q('spbRevMatAdjBtn')) q('spbRevMatAdjBtn').addEventListener('click', function () { adjOpen = !adjOpen; if (adjOpen) popOpen = false; buildBand(); if (q('spbRevMatAdjBtn')) q('spbRevMatAdjBtn').focus(); });
        const P = function () { return (T.params = M.normParams(T.params)); };
        const live = function (id, fn) { const e = q(id); if (!e) return; e.addEventListener('input', function () { fn(e); adjSet(); }); e.addEventListener('change', function () { fn(e); save(); adjSet(); }); };
        live('spbRevMatScale', function (e) { P().scale = M.normParams({ scale: posToScale(e.value) }).scale; });
        live('spbRevMatRot', function (e) { P().rotation = M.normParams({ rotation: e.value }).rotation; });
        live('spbRevMatStr', function (e) { P().strength = (Number(e.value) || 0) / 100; });
        live('spbRevMatSpecStr', function (e) { P().specStrength = (Number(e.value) || 0) / 100; });
        live('spbRevMatColStr', function (e) { const p = P(); if (p.colorMode === 'tint') p.colorDepth = (Number(e.value) || 0) / 100; else p.colorStrength = (Number(e.value) || 0) / 100; });
        if (q('spbRevMatTex')) q('spbRevMatTex').addEventListener('change', function (e) { T.texture = !!e.target.checked; save(); adjSet(); });
        if (q('spbRevMatColMode')) q('spbRevMatColMode').addEventListener('change', function (e) { P().colorMode = e.target.value === 'solid' ? 'solid' : 'tint'; save(); buildBand(); updateBar(); });
        live('spbRevMatCol', function (e) { T.lastColor = e.value; const on = q('spbRevMatColOn'); if (on && !on.checked) on.checked = true; P().color = e.value; });
        if (q('spbRevMatColOn')) q('spbRevMatColOn').addEventListener('change', function (e) { const c = q('spbRevMatCol'); P().color = e.target.checked ? (c ? c.value : '#d42a2a') : null; save(); adjSet(); });
        // [SPB-REV-FLAKE 2026-10-10] Flake row: Edit = Flake Studio aimed at the brush; Off = the brush without the flake
        if (q('spbRevMatFlakeEdit')) q('spbRevMatFlakeEdit').addEventListener('click', function () { try { root.SpbFlakeStudio.open({ target: 'brush', brushMode: T.mode }); } catch (_) {} });
        if (q('spbRevMatFlakeOff')) q('spbRevMatFlakeOff').addEventListener('click', function () { const np = M.normParams(T.params); np.flake = null; T.params = np; save(); buildBand(); updateBar(); });
        if (q('spbRevMatAdjReset')) q('spbRevMatAdjReset').addEventListener('click', function () { T.params = M.normParams(null); T.texture = false; save(); buildBand(); updateBar(); });
        if (q('spbRevMatPreset')) q('spbRevMatPreset').addEventListener('change', function (e) {
            const v = e.target.value;
            if (v === 'flake') { buildBand(); try { root.SpbFlakeStudio.open({ target: 'brush', brushMode: 'spec' }); } catch (_) {} return; }   // [SPB-REV-FLAKE 2026-10-10]
            setPreset(v);
            if (v === 'finish' && doc.getElementById('spbRevMatSpecFin')) openPicker(doc.getElementById('spbRevMatSpecFin'));   // "Any finish…" opens the full picker at once
        });
        Array.prototype.forEach.call(band.querySelectorAll('.spb-rm-chbtn'), function (b) {
            b.addEventListener('click', function () { const ch = +b.getAttribute('data-ch'); T.chan[ch] = T.chan[ch] ? 0 : 1; if (!T.chan.some(Boolean)) T.chan[ch] = 1; save(); buildBand(); updateBar(); });
        });
        Array.prototype.forEach.call(band.querySelectorAll('.spb-rm-num'), function (inp) {
            inp.addEventListener('change', function () {
                const p = preset(), ch = +inp.getAttribute('data-ch'), v = Math.max(0, Math.min(255, Math.round(Number(inp.value) || 0)));
                T.custom = { m: p.m, r: p.r, cc: p.cc };
                T.custom[['m', 'r', 'cc'][ch]] = v;
                if (T.presetId !== 'raw') { T.grain = p.grain || 0; }
                T.presetId = 'raw'; T.chan[ch] = 1; save(); buildBand(); updateBar();
            });
        });
        if (q('spbRevMatGrain')) q('spbRevMatGrain').addEventListener('input', function (e) { T.grain = Number(e.target.value) || 0; save(); });
        if (q('spbRevMatPickPaint')) q('spbRevMatPickPaint').addEventListener('change', function (e) { T.pickPaint = !!e.target.checked; save(); });
        if (q('spbRevMatWear')) q('spbRevMatWear').addEventListener('change', function (e) { T.wearType = e.target.value; save(); buildBand(); updateBar(); });
        if (q('spbRevMatClip')) q('spbRevMatClip').addEventListener('change', function (e) {
            try { const z = zones[selectedZoneIndex]; if (root.SPBZoneClip && z) root.SPBZoneClip.setOff(z, !e.target.checked); } catch (_) {}
        });
        if (q('spbRevMatClear')) q('spbRevMatClear').addEventListener('click', function () { if (!M.clearAll()) toast('Nothing to clear yet.'); else toast('Material layers cleared. Ctrl+Z brings them back.'); });
    }
    function showBrushControls(on) {
        BRUSH_IDS.forEach(function (id) { const e = doc.getElementById(id); if (e) e.style.display = on ? '' : 'none'; });
        try { if (root.SPBToolRow && root.SPBToolRow.state) { /* band refresh runs on its own observer */ } } catch (_) {}
    }
    let lastRead = null;
    function updateBar() {
        if (!ensureUi()) return;
        const t = tool();
        if (!t) { bar.style.display = 'none'; return; }
        bar.style.display = 'inline-flex';
        let sw = '', txt = '';
        if (t === 'material') {
            const url = swatchUrl(T.finishId);
            sw = url ? '<img class="spb-rm-sw" alt="" src="' + esc(url) + '">' : '<i class="spb-rm-sw" style="background:' + esc(finishSwatchHex(T.finishId)) + '"></i>';
            txt = '<b>' + esc(M.finishName(T.finishId)) + '</b>';
            if (studioOn()) {
                // [BRUSH-STUDIO 2026-10-10] mode + sliders; the read-back line once the preview shows this coat's spec
                const pl = M.paramsLabel(strokeParams(T.mode));
                const plan = '<span>' + esc(M.MODE_NAME[T.mode] + (T.mode === 'spec' && T.texture ? ' + texture' : '') + (pl ? ' · ' + pl : '')) + '</span>';
                if (lastRead && lastRead.kind === 'coat' && lastRead.finishId === T.finishId && lastRead.sig === M.psig(strokeParams(T.mode)) && lastRead.mode === T.mode) txt += plan + '<span>on car: M ' + lastRead.m + ' · R ' + lastRead.r + ' · CC ' + lastRead.cc + '</span>';
                else txt += plan;
            } else if (lastRead && lastRead.kind === 'coat' && lastRead.finishId === T.finishId && !!lastRead.keep === !!T.keep) txt += '<span>on car: M ' + lastRead.m + ' · R ' + lastRead.r + ' · CC ' + lastRead.cc + '</span>';
            else txt += '<span>' + (T.keep ? 'keeps your colour: spec + texture' : 'real finish: paint + spec') + '</span>';
        } else if (t === 'spec' && studioOn() && T.presetId === 'finish') {
            const url = swatchUrl(T.specFinish), pl = M.paramsLabel(strokeParams('spec'));
            sw = url ? '<img class="spb-rm-sw" alt="" src="' + esc(url) + '">' : '<i class="spb-rm-sw" style="background:' + esc(finishSwatchHex(T.specFinish)) + '"></i>';
            txt = '<b>Spec of ' + esc(M.finishName(T.specFinish)) + '</b><span>' + esc((T.texture ? 'paint colour stays + texture' : 'your paint stays') + (pl ? ' · ' + pl : '')) + '</span>';
            if (lastRead && lastRead.kind === 'coat' && lastRead.finishId === T.specFinish && lastRead.mode === 'spec') txt += '<span>on car: M ' + lastRead.m + ' · R ' + lastRead.r + ' · CC ' + lastRead.cc + '</span>';
        } else if (t === 'spec') {
            const p = preset(), f = R.floored(p.m, p.r, p.cc), ch = T.chan;
            const rgb = 'rgb(' + Math.round(f.m) + ',' + Math.round(255 - f.r) + ',' + Math.round(255 - Math.min(255, f.cc)) + ')';
            sw = '<i class="spb-rm-sw spb-rm-specsw" style="background:linear-gradient(135deg,' + (p.id === 'picked' && T.picked ? 'rgb(' + T.picked.paint.join(',') + ')' : '#5b6370') + ' 0 50%,' + rgb + ' 50% 100%)"></i>';
            txt = '<b>' + esc(p.name) + (p.id === 'picked' && T.picked && T.picked.near ? ' (reads as ' + esc(T.picked.near) + ')' : '') + '</b><span>' +
                (ch[0] ? 'M ' + Math.round(f.m) : '<s>M</s>') + ' · ' + (ch[1] ? 'R ' + Math.round(f.r) : '<s>R</s>') + ' · ' + (ch[2] ? 'CC ' + Math.round(f.cc) : '<s>CC</s>') + '</span>';
            if (lastRead && lastRead.kind === 'layer') txt += '<span>on car: M ' + lastRead.m + ' · R ' + lastRead.r + ' · CC ' + lastRead.cc + '</span>';
        } else if (t === 'wear') {
            const w = R.WEAR.find(function (x) { return x.id === T.wearType; });
            sw = '<i class="spb-rm-sw spb-rm-wear-' + esc(T.wearType) + '"></i>';
            const spec = { dirt: 'M 22 · R 178-236 · CC 196-248', rubber: 'M 0 · R 150-178 · CC 205-230', chips: 'metal core M 228 R 62-88 · primer M 0 R 205-225 · CC 255' }[T.wearType] || '';
            txt = '<b>' + esc(w ? w.name : '') + '</b><span>' + spec + '</span>';
            if (lastRead && lastRead.kind === 'layer') txt += '<span>on car: M ' + lastRead.m + ' · R ' + lastRead.r + ' · CC ' + lastRead.cc + '</span>';
        } else {
            const p = T.picked;
            sw = p ? '<i class="spb-rm-sw" style="background:rgb(' + p.paint.join(',') + ')"></i>' : '<i class="spb-rm-sw"></i>';
            txt = p ? '<b>Picked</b><span>M ' + p.m + ' · R ' + p.r + ' · CC ' + p.cc + (p.near ? ' · reads as ' + esc(p.near) : '') + '</span>' : '<b>Spec Eyedropper</b><span>click the car</span>';
        }
        bar.innerHTML = sw + '<span class="spb-rm-bartxt">' + txt + '</span>';
        // two lines fit the fixed 45 px bar: once the car has been read back, that line replaces the planned values (full text on hover)
        bar.title = Array.prototype.map.call(bar.querySelectorAll('.spb-rm-bartxt > *'), function (n) { return n.textContent; }).join(' | ');
    }

    // live readout: after each LIVE PREVIEW, read the real spec map inside what was just painted
    let lastBox = null;
    M.on(function (what, info) {
        if (what === 'dab') queue(info);
        else if (what === 'redraw' || what === 'reset') { if (tool()) redrawAll(); }
        else if (what === 'end' && info) {
            lastBox = { box: info.box, tool: (info.label || '').split(':')[0] };
            // dabs queued until the stroke had a direction (click without drag) land in endStroke: repaint the box
            if (info.box) queue({ x: info.box[0], y: info.box[1], w: info.box[2] - info.box[0], h: info.box[3] - info.box[1] });
        }
    });
    function readBack() {
        const t = tool(); if (!t || !root.SPBSpecPngPixels) return;
        const src = specImageSrc(); if (!src) return;
        const S = M.state;
        root.SPBSpecPngPixels.load(src).then(function (sp) {
            const W = S.W, H = S.H; if (!W) return;
            let sm = 0, sr = 0, sc = 0, n = 0, kind = '', fid = '', keepRead = false, rsig = '', rmode = '';
            const fromFin = t === 'spec' && studioOn() && T.presetId === 'finish';
            if (t === 'material' || fromFin) {
                let c = null;
                if (studioOn()) {
                    // [BRUSH-STUDIO 2026-10-10] read the SPEC coat of the current finish + mode + sliders (Paint only has none: nothing to read)
                    rmode = fromFin ? 'spec' : T.mode; rsig = M.psig(strokeParams(rmode));
                    const f = fromFin ? T.specFinish : T.finishId;
                    if (rmode === 'paint') return;
                    c = S.coats.find(function (x) { return x.plane === 'spec' && x.finishId === f && !!x.keep === (rmode === 'spec' && !!T.texture) && x.psig === rsig; });
                } else c = S.coats.find(function (x) { return x.finishId === T.finishId && !!x.keep === !!T.keep; });
                if (!c || !c.box) return;
                kind = 'coat'; fid = c.finishId; keepRead = !!c.keep;
                const b = c.box;
                const px0 = Math.floor(b[0] * sp.width / W), px1 = Math.ceil(b[2] * sp.width / W), py0 = Math.floor(b[1] * sp.height / H), py1 = Math.ceil(b[3] * sp.height / H);
                for (let y = py0; y < py1; y++) for (let x = px0; x < px1; x++) {
                    const dx = Math.min(W - 1, Math.floor((x + 0.5) * W / sp.width)), dy = Math.min(H - 1, Math.floor((y + 0.5) * H / sp.height));
                    if (c.mask[dy * W + dx] < 250) continue;
                    const k = (y * sp.width + x) * 4; sm += sp.data[k]; sr += sp.data[k + 1]; sc += sp.data[k + 2]; n++;
                }
            } else if (S.sc && S.lb) {
                kind = 'layer';
                const b = (lastBox && lastBox.box) || S.lb;
                const px0 = Math.floor(b[0] * sp.width / W), px1 = Math.ceil(b[2] * sp.width / W), py0 = Math.floor(b[1] * sp.height / H), py1 = Math.ceil(b[3] * sp.height / H);
                for (let y = py0; y < py1; y++) for (let x = px0; x < px1; x++) {
                    const dx = Math.min(W - 1, Math.floor((x + 0.5) * W / sp.width)), dy = Math.min(H - 1, Math.floor((y + 0.5) * H / sp.height));
                    const i = dy * W + dx; if (Math.max(S.sc[i * 3], S.sc[i * 3 + 1], S.sc[i * 3 + 2]) < 250) continue;
                    const k = (y * sp.width + x) * 4; sm += sp.data[k]; sr += sp.data[k + 1]; sc += sp.data[k + 2]; n++;
                }
            }
            if (!n) return;
            lastRead = { kind: kind, finishId: fid, keep: keepRead, sig: rsig, mode: rmode, m: Math.round(sm / n), r: Math.round(sr / n), cc: Math.round(sc / n), n: n };
            root.__spbRevMatLastRead = lastRead;
            updateBar();
        }).catch(function () {});
    }
    function watchPreview() {
        const s = doc.getElementById('livePreviewSpecImg');
        if (!s || s.__spbRevMat) return;
        s.__spbRevMat = true;
        s.addEventListener('load', function () { setTimeout(readBack, 0); });
    }

    // ---------------------------------------------------------------- toolbar menu + keys + hints
    function injectMenu() {
        if (doc.getElementById('spbRevMatMenu')) return true;
        const anchor = doc.getElementById('spbRetouchMenu');
        if (!anchor || !anchor.parentNode) return false;
        const d = el('details', { class: 'spb-tb-menu', id: 'spbRevMatMenu' });
        d.innerHTML = '<summary class="spb-tb-summary" title="Material tools: paint SPB finishes, spec and race wear straight onto the car">Material <span class="spb-tb-caret">▾</span></summary>' +
            '<div class="spb-tb-pop">' +
            '<button type="button" class="vtool-btn" data-rm="rev-material" title="Material Brush (U): brush any SPB finish onto the car, paint + spec together"><span class="spb-mi-ico">◍</span> Material Brush <kbd>U</kbd></button>' +
            '<button type="button" class="vtool-btn" data-rm="rev-spec" title="Spec Brush: paint metallic / roughness / clearcoat only, paint stays"><span class="spb-mi-ico">◐</span> Spec Brush</button>' +
            '<button type="button" class="vtool-btn" data-rm="rev-wear" title="Wear Brush: dirt, rubber marks, stone chips (paint + spec in one stroke)"><span class="spb-mi-ico">⁘</span> Wear Brush</button>' +
            '<button type="button" class="vtool-btn" data-rm="rev-specpick" title="Spec Eyedropper: click the car to pick its paint + spec, then brush with it"><span class="spb-mi-ico">⌖</span> Spec Eyedropper</button>' +
            '<button type="button" class="vtool-btn" data-rm="clear" title="Remove every Material, Spec and Wear stroke (Ctrl+Z brings them back)"><span class="spb-mi-ico">✕</span> Clear Material Strokes</button>' +
            '</div>';
        anchor.parentNode.insertBefore(d, anchor.nextSibling);
        d.addEventListener('click', function (e) {
            const b = e.target.closest && e.target.closest('[data-rm]');
            if (!b) return;
            e.preventDefault();
            d.removeAttribute('open');
            if (b.getAttribute('data-rm') === 'clear') { toast(M.clearAll() ? 'Material strokes cleared. Ctrl+Z brings them back.' : 'No material strokes to clear.'); return; }
            setMode(b.getAttribute('data-rm'));
        });
        return true;
    }
    function typing(e) {
        const t = e.target;
        if (!t) return false;
        const tag = (t.tagName || '').toLowerCase();
        return tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable;
    }
    doc.addEventListener('keydown', function (e) {
        if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || typing(e)) return;
        if ((e.key || '').toLowerCase() !== 'u') return;
        const pc = doc.getElementById('paintCanvas'); if (!pc) return;
        e.preventDefault();
        if (e.shiftKey) { const i = CYCLE.indexOf(mode()); setMode(CYCLE[(i + 1) % CYCLE.length]); }
        else setMode('rev-material');
    });
    // Alt erases: show it on the ring (dashed) while held
    root.addEventListener('keydown', function (e) { if (e.key === 'Alt' && ring && tool()) ring.style.borderStyle = 'dashed'; });
    root.addEventListener('keyup', function (e) { if (e.key === 'Alt' && ring) ring.style.borderStyle = 'solid'; });
    function installGuide() {
        try {
            if (root.TOOL_GUIDE && typeof root.TOOL_GUIDE === 'object') Object.keys(GUIDE).forEach(function (k) { root.TOOL_GUIDE[k] = GUIDE[k]; });
        } catch (_) {}
    }

    // ---------------------------------------------------------------- mode sync
    let lastMode = null;
    // [SPB-TICKETS-FIX 2026-10-10 T-6] (INTEGRATION-QA: a layer mask kept its "Edit" state under a coat tool and the stroke
    // silently went to the coat). Now: picking a coat tool ENDS mask editing (toast says so); pressing Edit on a mask while a coat
    // tool is active hands over to the Brush so the stroke paints the mask. Kill switch window.SPB_TFIX_OFF / SPB_TFIX_T6_OFF.
    let tfMaskSeen = null;
    function tfMaskGuard(t, entered) {
        if (root.SPB_TFIX_OFF || root.SPB_TFIX_T6_OFF) return;
        try {
            const PM = root.SPBPcLayerMask;
            const id = (PM && typeof PM.editing === 'function') ? PM.editing() : null;
            if (!t || !id) { tfMaskSeen = id || null; return; }
            if (entered) { PM.setEdit(id, false); tfMaskSeen = null; toast('Mask editing ended: the ' + NAMES[t] + ' paints a coat, not the mask.'); }
            else if (id !== tfMaskSeen) { tfMaskSeen = id; if (typeof root.setCanvasMode === 'function') { root.setCanvasMode('brush'); toast('Brush picked: white reveals, black hides on the layer mask.'); } }
        } catch (_) {}
    }
    function sync(force) {
        const m = mode(), t = MODES[m] || null;
        if (!force && m === lastMode) { tfMaskGuard(t, false); syncOverlayBox(); return; }
        const was = MODES[lastMode] || null;
        lastMode = m;
        tfMaskGuard(t, !was);   // entering a coat tool from a non-coat tool (switching between coat tools keeps whatever state it had)
        const menu = doc.getElementById('spbRevMatMenu');
        if (menu) menu.classList.toggle('spb-rm-on', !!t);
        const pc = doc.getElementById('paintCanvas');
        if (t) {
            M.ensure();
            if (pc) pc.style.cursor = t === 'pick' ? 'crosshair' : 'none';
            buildBand(); updateBar(); overlay(); redrawAll(); watchPreview();
        } else {
            if (band) { band.style.display = 'none'; band.innerHTML = ''; builtFor = ''; }
            popOpen = false; hostClass();
            if (bar) bar.style.display = 'none';
            hideRing();
            if (was && pc && pc.style.cursor === 'none') pc.style.cursor = '';
            if (drag) onUp(null);
        }
        syncOverlayBox();
    }
    function wrapSetMode() {
        const cur = root.setCanvasMode;
        if (typeof cur !== 'function' || cur.__spbRevMat) return;
        const w = function () { const r = cur.apply(this, arguments); try { sync(true); } catch (_) {} return r; };
        w.__spbRevMat = true;
        root.setCanvasMode = w;
    }

    function boot() {
        let tries = 0;
        const t = setInterval(function () {
            tries++;
            installGuide(); wrapPicker(); wrapSetMode(); M.wrapSerializer();
            const ok = injectMenu();
            if ((ok && tries > 6) || tries > 60) clearInterval(t);
        }, 500);
        setInterval(function () { sync(false); if (tool() && builtFor !== tool()) buildBand(); fitCheck(); }, 200);
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot();

    root.SPBRevMaterialUI = { settings: T, setMode: setMode, preset: preset, setPreset: setPreset, redrawAll: redrawAll, readBack: readBack, pickAt: pickAt, sync: sync,
        setStudioMode: setStudioMode, strokeParams: strokeParams, studioOn: studioOn, buildBand: function () { buildBand(); updateBar(); } };   // [BRUSH-STUDIO 2026-10-10] additive
})(typeof window !== 'undefined' ? window : null);
