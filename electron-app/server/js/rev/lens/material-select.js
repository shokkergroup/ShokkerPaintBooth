/* ============================================================================
 * [SPB-REV-LENS 2026-10-10] MATERIAL SELECT  (Select > Material...)
 * Select by MATERIAL in spec space, not by colour: "same material as this
 * pixel" (tolerance on the iRacing spec channels R metal / G rough / B coat
 * [/ A mask]), or presets: All Chrome, All Matte, All Gloss Clear,
 * Roughness < N, Metallic > N.  Reads the spec map the Live Preview already
 * shows (exact PNG bytes via SPBShineCore / SPBRevLens.getSpec) - never renders.
 *
 * The result becomes a NORMAL selection: it is written to the active Zone's
 * regionMask through the same public bridges Color Range uses
 * (_spbPushZoneMaskUndoSnapshot = one undo entry, SPBPcSelection.compose for
 * Replace / Add / Subtract, SPBPenPath.featherMask for the Feather option,
 * autoActivateZoneApplyArea + spbRefreshZoneMaskUI to settle), so Mask >
 * Grow / Feather / Invert, fills, zones and brushes all work on it.
 * With "Shine the selection" on, the Shine Lens spotlights what is selected.
 *
 * Kill switch: window.SPB_REV_LENS_OFF / localStorage SPB_REV_LENS_OFF='1'.
 * ==========================================================================*/
(function () {
    'use strict';
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const C = window.SPBShineCore;
    if (!C || C.killed()) return;

    const D = { el: null, st: null, over: null, pos: null, swallow: false };

    function toast(m, kind) { if (typeof window.showToast === 'function') window.showToast(m, kind || 'info'); }
    function q(id) { return document.getElementById(id); }
    function lens() { return window.SPBRevLens && !window.SPBRevLens.off ? window.SPBRevLens : null; }

    // ------------------------------------------------------------ sampling
    function median(spec, w, h, x, y) {
        const ch = [[], [], [], []];
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
            const xx = Math.max(0, Math.min(w - 1, x + dx)), yy = Math.max(0, Math.min(h - 1, y + dy));
            const o = (yy * w + xx) * 4;
            for (let k = 0; k < 4; k++) ch[k].push(spec[o + k]);
        }
        const m = ch.map(function (a) { a.sort(function (p, r) { return p - r; }); return a[4]; });
        return { m: m[0], r: m[1], cc: m[2], a: m[3], x, y };
    }

    function recompute() {
        const S = D.st;
        if (!S || !S.spec) return;
        const t0 = performance.now();
        const w = S.spec.w, h = S.spec.h, sp = S.spec.data;
        let cover = null;
        if (S.preset) {
            const n = S.preset === 'roughLt' ? S.roughN : S.preset === 'metalGt' ? S.metalN : 0;
            cover = C.presetCoverage(sp, w, h, S.preset, n).cover;
        } else if (S.ops.length) {
            cover = new Uint8Array(w * h);
            S.ops.forEach(function (op) {
                let c = S.whole && C.materialCoverage
                    ? C.materialCoverage(sp, w, h, op.sample.x, op.sample.y, S.tol, S.fuzz, S.chans, 4).cover
                    : C.sameCoverage(sp, w, h, op.sample, S.tol, S.fuzz, S.chans).cover;
                if (S.contig) c = C.keepConnected(c, w, h, op.sample.x, op.sample.y).cover;
                if (op.op === '-') { for (let i = 0; i < c.length; i++) if (c[i]) { const v = cover[i] - c[i]; cover[i] = v > 0 ? v : 0; } }
                else { for (let i = 0; i < c.length; i++) if (c[i] > cover[i]) cover[i] = c[i]; }
            });
        }
        S.cover = cover;
        let n = 0;
        if (cover) for (let i = 0; i < cover.length; i++) if (cover[i] > 127) n++;
        S.count = n; S.ms = performance.now() - t0;
        const info = q('spbMtInfo');
        if (info) {
            const scale = (q('paintCanvas') ? q('paintCanvas').width : w) / w;
            info.textContent = cover ? (Math.round(n * scale * scale).toLocaleString() + ' px selected (' + (100 * n / (w * h)).toFixed(1) + '% of the sheet) - ' + S.ms.toFixed(0) + ' ms')
                : 'Click the car or the Live Preview to pick a material, or use a preset.';
        }
        drawOverlay();
        const L = lens();
        if (L && L.setSelectionMask) L.setSelectionMask(S.shine && cover ? cover : null, w, h);
    }
    let raf = 0;
    function schedule() { if (!raf) raf = requestAnimationFrame(function () { raf = 0; recompute(); }); }

    // ------------------------------------------------------------ overlay on the source canvas
    function ensureOverlay() {
        const rc = q('regionCanvas'), pc = q('paintCanvas');
        if (!rc || !pc || !D.st || !D.st.spec) return null;
        let ov = D.over;
        if (!ov || !ov.parentNode) {
            ov = document.createElement('canvas');
            ov.id = 'spbMatSelOverlay';
            ov.className = 'spb-matsel-overlay';
            rc.parentNode.insertBefore(ov, rc.nextSibling);
            D.over = ov;
        }
        if (ov.width !== D.st.spec.w) ov.width = D.st.spec.w;
        if (ov.height !== D.st.spec.h) ov.height = D.st.spec.h;
        ov.style.width = rc.style.width || pc.style.width || (rc.offsetWidth + 'px');
        ov.style.height = rc.style.height || pc.style.height || (rc.offsetHeight + 'px');
        return ov;
    }
    function drawOverlay() {
        const ov = ensureOverlay();
        if (!ov) return;
        const ctx = ov.getContext('2d');
        const S = D.st;
        if (!S.cover) { ctx.clearRect(0, 0, ov.width, ov.height); return; }
        const img = ctx.createImageData(ov.width, ov.height);
        const d = img.data, m = S.cover;
        for (let i = 0, o = 0; i < m.length; i++, o += 4) {
            const v = m[i];
            if (v) { d[o] = 63; d[o + 1] = 186; d[o + 2] = 181; d[o + 3] = v * 0.55; }
        }
        ctx.putImageData(img, 0, 0);
    }

    // ------------------------------------------------------------ picking
    function specXY(ev) {
        const S = D.st;
        const t = ev.target;
        if (!t || !S || !S.spec) return null;
        if (t.id === 'paintCanvas') {
            const pos = typeof window.getPixelAt === 'function' ? window.getPixelAt(ev) : null;
            const pc = q('paintCanvas');
            if (!pos || !pc) return null;
            return { x: Math.min(S.spec.w - 1, Math.floor(pos.x * S.spec.w / pc.width)), y: Math.min(S.spec.h - 1, Math.floor(pos.y * S.spec.h / pc.height)) };
        }
        if (t.id === 'livePreviewImg' || t.id === 'spbShineCanvas') {
            const L = lens();
            const cr = L && L._test ? L._test.contentRect() : null;
            if (!cr) return null;
            const u = (ev.clientX - cr.left) / cr.width, v = (ev.clientY - cr.top) / cr.height;
            if (u < 0 || v < 0 || u >= 1 || v >= 1) return null;
            return { x: Math.floor(u * S.spec.w), y: Math.floor(v * S.spec.h) };
        }
        return null;
    }
    function onDown(e) {
        const S = D.st;
        if (!S || e.button !== 0) return;
        const p = specXY(e);
        if (!p) return;
        e.stopImmediatePropagation(); e.preventDefault();
        D.swallow = true;       // eat the click that would open the preview lightbox
        setTimeout(function () { D.swallow = false; }, 800);
        const sample = S.whole && C.avgSample ? C.avgSample(S.spec.data, S.spec.w, S.spec.h, p.x, p.y, 4)
            : median(S.spec.data, S.spec.w, S.spec.h, p.x, p.y);
        const op = e.shiftKey ? '+' : e.altKey ? '-' : 's';
        S.preset = null;
        if (op === 's') S.ops = [{ op: '+', sample }];
        else S.ops.push({ op, sample });
        S.last = sample;
        showSample(sample);
        markPreset();
        recompute();
    }
    function onClick(e) { if (D.swallow) { D.swallow = false; e.stopImmediatePropagation(); e.preventDefault(); } }
    function onKey(e) {
        if (!D.st) return;
        if (e.key === 'Escape') { close(false); e.stopPropagation(); e.preventDefault(); }
        else if (e.key === 'Enter' && !(e.target && /^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(e.target.tagName))) { close(true); e.stopPropagation(); e.preventDefault(); }
    }
    function showSample(s) {
        const sw = q('spbMtSwatch'), nm = q('spbMtName'), vals = q('spbMtVals');
        if (!s) return;
        if (sw) sw.style.background = 'rgb(' + s.m + ',' + s.r + ',' + s.cc + ')';
        if (nm) nm.textContent = C.nameOf(s.m, s.r, s.cc);
        if (vals) vals.textContent = 'Metal ' + s.m + ' · Rough ' + s.r + ' · Coat ' + s.cc + ' · Mask ' + s.a;
    }
    function markPreset() {
        if (!D.el) return;
        D.el.querySelectorAll('[data-p]').forEach(function (b) { b.classList.toggle('on', b.dataset.p === (D.st && D.st.preset)); });
    }

    // ------------------------------------------------------------ commit (same contract as Color Range)
    function commit() {
        const S = D.st;
        if (!S || !S.cover) { toast('Material Select: pick a material or a preset first'); return false; }
        const targetIndex = typeof selectedZoneIndex === 'number' ? selectedZoneIndex : -1;
        const zone = typeof zones !== 'undefined' ? zones[targetIndex] : null;
        const pc = q('paintCanvas');
        if (!zone || !pc) { toast('Select a Zone before using Material Select'); return false; }
        const cw = pc.width, ch = pc.height, n = cw * ch;
        const cover = C.upscale(S.cover, S.spec.w, S.spec.h, cw, ch);
        const cur = zone.regionMask instanceof Uint8Array && zone.regionMask.length === n ? zone.regionMask : new Uint8Array(n);
        const mode = S.mode || 'replace';
        let next = window.SPBPcSelection && window.SPBPcSelection.compose ? window.SPBPcSelection.compose(cur, cover, mode)
            : (mode === 'replace' ? cover : cur);
        const featherPx = parseInt((q('selectionFeather') || {}).value || 0, 10) || 0;
        if (featherPx > 0 && window.SPBPenPath && window.SPBPenPath.featherMask) next = window.SPBPenPath.featherMask(next, cw, ch, featherPx);
        let changed = 0, sel = 0;
        for (let i = 0; i < n; i++) { if (next[i] !== cur[i]) changed++; if (next[i] > 127) sel++; }
        if (!changed) { toast('Material Select skipped: the selection already matches'); return false; }
        if (typeof window._spbPushZoneMaskUndoSnapshot !== 'function') { toast('Material Select: selection history unavailable - reload the booth'); return false; }
        window._spbPushZoneMaskUndoSnapshot(targetIndex);
        zone.regionMask = next;
        if (sel > 0) {
            if (typeof autoActivateZoneApplyArea === 'function') autoActivateZoneApplyArea(targetIndex, 'wand');
            else zone.useRegion = true;
        } else zone.useRegion = false;
        if (typeof window.spbRefreshZoneMaskUI === 'function') window.spbRefreshZoneMaskUI();
        else if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
        toast('Material Select ' + mode + ': ' + sel.toLocaleString() + ' pixels', 'success');
        return true;
    }

    // ------------------------------------------------------------ panel
    function clampPos(el, left, top) {
        const w = el.offsetWidth || 284, h = el.offsetHeight || 380;
        const pane = q('canvasViewport'), floor = pane ? Math.max(8, Math.round(pane.getBoundingClientRect().top)) : 8;
        return { left: Math.max(8, Math.min(window.innerWidth - w - 8, left)), top: Math.max(floor, Math.min(window.innerHeight - Math.min(h, window.innerHeight - 16) - 8, top)) };
    }
    function place(el) {
        let left, top;
        if (D.pos) { left = D.pos.left; top = D.pos.top; }
        else {
            const pane = q('canvasViewport') || (q('paintCanvas') && q('paintCanvas').parentElement);
            const r = pane ? pane.getBoundingClientRect() : { top: 130, right: window.innerWidth };
            left = r.right - (el.offsetWidth || 284) - 16; top = r.top + 8;
            // keep the Live Preview clear (the shine shows there): sit at the right edge of the source pane
            const img = q('livePreviewImg'), pv = img ? (img.closest('.preview-inner') || img.parentElement) : null;
            const pr = pv ? pv.getBoundingClientRect() : null;
            if (pr && pr.width > 40 && pr.left - (el.offsetWidth || 284) - 12 >= (r.left || 0) + 8) left = pr.left - (el.offsetWidth || 284) - 12;
        }
        const p = clampPos(el, left, top);
        el.style.left = p.left + 'px'; el.style.top = p.top + 'px';
    }
    // keep the panel on screen when the window shrinks (e.g. 1920 -> 1100 wide)
    function onResize() { if (D.el && D.el.isConnected) { if (D.pos) D.pos = clampPos(D.el, D.pos.left, D.pos.top); place(D.el); } }
    function wireDrag(el, handle) {
        handle.addEventListener('pointerdown', function (e) {
            if (e.button !== 0 || (e.target.closest && e.target.closest('button'))) return;
            const r = el.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
            try { handle.setPointerCapture(e.pointerId); } catch (_) { }
            const mv = function (ev) { const p = clampPos(el, ev.clientX - dx, ev.clientY - dy); el.style.left = p.left + 'px'; el.style.top = p.top + 'px'; D.pos = p; };
            const up = function () { handle.removeEventListener('pointermove', mv); handle.removeEventListener('pointerup', up); handle.removeEventListener('pointercancel', up); };
            handle.addEventListener('pointermove', mv); handle.addEventListener('pointerup', up); handle.addEventListener('pointercancel', up);
            e.preventDefault();
        });
    }

    async function open() {
        if (D.st) return true;
        if (typeof zones === 'undefined' || !zones[selectedZoneIndex]) { toast('Select a Zone before using Material Select'); return false; }
        const L = lens();
        let spec = null;
        try { spec = L && L.getSpec ? await L.getSpec() : null; } catch (_) { spec = null; }
        if (!spec || !spec.data) { toast('Material Select reads the Live Preview spec map - wait for the preview to finish'); return false; }
        const uiMode = (q('selectionMode') || {}).value;
        D.st = { spec, ops: [], preset: null, tol: 12, fuzz: 6, chans: [1, 1, 1, 0], contig: false, whole: true, roughN: 40, metalN: 128,
            mode: uiMode === 'add' || uiMode === 'subtract' ? uiMode : 'replace', shine: true, cover: null, count: 0,
            prevLens: L && L.getMode ? L.getMode() : 'off' };
        const el = document.createElement('div');
        el.id = 'spbMatSelDlg';
        el.className = 'spb-matsel';
        el.setAttribute('role', 'dialog');
        el.setAttribute('aria-label', 'Material Select');
        el.innerHTML = [
            '<div class="mt-title" id="spbMtTitle"><span>Material Select</span><button type="button" class="mt-x" id="spbMtX" title="Cancel (Esc)" aria-label="Close Material Select">×</button></div>',
            '<div class="mt-sample"><span class="mt-sw" id="spbMtSwatch"></span><div class="mt-sv"><div class="mt-name" id="spbMtName">Pick A Material</div><div class="mt-vals" id="spbMtVals">Click the car or the Live Preview</div></div></div>',
            '<div class="mt-row"><label for="spbMtTol">Tolerance</label><input id="spbMtTol" type="range" min="0" max="80" value="12"><input id="spbMtTolN" type="number" min="0" max="80" value="12" aria-label="Tolerance value"></div>',
            '<div class="mt-row"><label for="spbMtFuzz">Soft Edge</label><input id="spbMtFuzz" type="range" min="0" max="64" value="6"><input id="spbMtFuzzN" type="number" min="0" max="64" value="6" aria-label="Soft edge value"></div>',
            '<div class="mt-row mt-chk"><span class="mt-lbl">Match</span><label><input id="spbMtChM" type="checkbox" checked> Metal</label><label><input id="spbMtChR" type="checkbox" checked> Rough</label><label><input id="spbMtChC" type="checkbox" checked> Coat</label><label><input id="spbMtChA" type="checkbox"> Mask</label></div>',
            '<div class="mt-row"><label title="Treat a textured finish (carbon weave, metal flake, candy) as one material: compares small neighbourhoods instead of single pixels."><input id="spbMtWhole" type="checkbox" checked> Match Whole Finish</label>' +
            '<label><input id="spbMtContig" type="checkbox"> Contiguous</label></div>',
            '<div class="mt-sep">Presets</div>',
            '<div class="mt-presets"><button type="button" class="mt-btn" data-p="chrome" title="' + C.PRESETS.chrome.why + '">All Chrome</button><button type="button" class="mt-btn" data-p="matte" title="' + C.PRESETS.matte.why + '">All Matte</button><button type="button" class="mt-btn" data-p="glossclear" title="' + C.PRESETS.glossclear.why + '">All Gloss Clear</button></div>',
            '<div class="mt-row mt-num"><button type="button" class="mt-btn" data-p="roughLt" title="Roughness (G) below N">Rough Below</button><input id="spbMtRoughN" type="number" min="0" max="255" value="40" aria-label="Roughness threshold"><button type="button" class="mt-btn" data-p="metalGt" title="Metallic (R) above N">Metal Above</button><input id="spbMtMetalN" type="number" min="0" max="255" value="128" aria-label="Metallic threshold"></div>',
            '<div class="mt-row"><label for="spbMtMode">Apply As</label><select id="spbMtMode"><option value="replace">Replace</option><option value="add">Add</option><option value="subtract">Subtract</option></select></div>',
            '<div class="mt-row"><label><input id="spbMtShine" type="checkbox" checked> Shine The Selection</label></div>',
            '<div class="mt-hint" id="spbMtInfo">Click the car or the Live Preview to pick a material, or use a preset.</div>',
            '<div class="mt-row mt-btns"><button type="button" class="mt-btn" id="spbMtReset">Reset</button><button type="button" class="mt-btn" id="spbMtCancel">Cancel</button><button type="button" class="mt-btn mt-ok" id="spbMtOk">OK</button></div>',
            '<div class="mt-hint">Reads the spec map the Live Preview shows. Shift+click adds, Alt+click subtracts. OK makes a normal selection (Feather and the Mask menu work on it). Esc cancels.</div>',
        ].join('');
        document.body.appendChild(el);
        D.el = el;
        place(el);
        const S = D.st;
        q('spbMtMode').value = S.mode;
        const pair = function (a, b, key) {
            q(a).oninput = function () { S[key] = +this.value; q(b).value = this.value; schedule(); };
            q(b).oninput = function () { const v = Math.max(+q(a).min, Math.min(+q(a).max, +this.value || 0)); S[key] = v; q(a).value = v; schedule(); };
        };
        pair('spbMtTol', 'spbMtTolN', 'tol');
        pair('spbMtFuzz', 'spbMtFuzzN', 'fuzz');
        ['spbMtChM', 'spbMtChR', 'spbMtChC', 'spbMtChA'].forEach(function (id, k) { q(id).onchange = function () { S.chans[k] = this.checked ? 1 : 0; schedule(); }; });
        q('spbMtContig').onchange = function () { S.contig = this.checked; schedule(); };
        q('spbMtWhole').onchange = function () { S.whole = this.checked; schedule(); };
        q('spbMtRoughN').oninput = function () { S.roughN = Math.max(0, Math.min(255, +this.value || 0)); if (S.preset === 'roughLt') schedule(); };
        q('spbMtMetalN').oninput = function () { S.metalN = Math.max(0, Math.min(255, +this.value || 0)); if (S.preset === 'metalGt') schedule(); };
        q('spbMtMode').onchange = function () { S.mode = this.value; };
        q('spbMtShine').onchange = function () {
            S.shine = this.checked;
            const Lx = lens();
            if (Lx && Lx.setMode) Lx.setMode(S.shine ? (S.prevLens === 'off' ? 'full' : S.prevLens) : S.prevLens);
            schedule();
        };
        el.querySelectorAll('[data-p]').forEach(function (b) {
            b.onclick = function () { S.preset = b.dataset.p; S.ops = []; markPreset(); schedule(); };
        });
        q('spbMtReset').onclick = function () { S.ops = []; S.preset = null; S.cover = null; markPreset(); recompute(); };
        q('spbMtCancel').onclick = function () { close(false); };
        q('spbMtX').onclick = function () { close(false); };
        q('spbMtOk').onclick = function () { close(true); };
        wireDrag(el, q('spbMtTitle'));
        document.addEventListener('keydown', onKey, true);
        // pointerdown (capture, window): runs before the canvas tools and the Shine canvas' own
        // drag/lightbox handler, which use pointer events and would otherwise also act on the pick.
        window.addEventListener('pointerdown', onDown, true);
        window.addEventListener('click', onClick, true);
        window.addEventListener('resize', onResize);
        if (L && L.setMode && S.prevLens === 'off') L.setMode('full');
        ensureOverlay();
        recompute();
        return true;
    }

    function close(apply) {
        const S = D.st;
        if (!S) return false;
        let ok = false;
        if (apply) ok = commit();
        window.removeEventListener('pointerdown', onDown, true);
        window.removeEventListener('resize', onResize);
        window.removeEventListener('click', onClick, true);
        document.removeEventListener('keydown', onKey, true);
        if (raf) { cancelAnimationFrame(raf); raf = 0; }
        if (D.el && D.el.parentNode) D.el.parentNode.removeChild(D.el);
        D.el = null;
        if (D.over) { const c = D.over.getContext('2d'); c.clearRect(0, 0, D.over.width, D.over.height); }
        const L = lens();
        if (L && L.setSelectionMask) L.setSelectionMask(null);
        if (L && L.setMode) L.setMode(S.prevLens || 'off');
        D.st = null;
        return ok;
    }

    // ------------------------------------------------------------ menu entry: Select > Material...
    const MENU_ICO = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8l5.6 3.2v6L8 14.2 2.4 11V5z"/><path d="M2.4 5L8 8.2 13.6 5M8 8.2v6"/></svg>';
    function ensureMenu() {
        if (q('vtMaterialSelect')) return true;
        const cr = q('vtColorRange');
        if (!cr || !cr.parentNode) return false;
        const b = document.createElement('button');
        b.id = 'vtMaterialSelect';
        b.type = 'button';
        b.className = 'vtool-btn';
        b.title = 'Material… — select by material in the spec map, not by colour: click a spot to pick everything made of the same material, or use a preset (All Chrome, All Matte, All Gloss Clear, Roughness <, Metallic >). Makes a normal selection.';
        b.setAttribute('aria-label', 'Material Select');
        b.innerHTML = '<span class="spb-mi-ico spb-rev-ico">' + MENU_ICO + '</span> Material…';
        b.addEventListener('click', function () {
            const det = b.closest('details'); if (det) det.removeAttribute('open');
            open();
        });
        cr.parentNode.insertBefore(b, cr.nextSibling);
        return true;
    }
    function boot() {
        ensureMenu();
        setInterval(ensureMenu, 2500);
    }
    window.spbOpenMaterialSelect = open;
    window.SPBRevMaterialSelect = { open, close, commit, isOpen: function () { return !!D.st; }, _state: function () { return D.st; }, recompute };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
