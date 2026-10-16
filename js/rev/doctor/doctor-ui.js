/* [SPB-REV-DOCTOR 2026-10-10] Spec Doctor: a one-click audit of the car's spec map (the exact pixels RENDER writes)
 * against the mistakes that make real iRacing paints look wrong in the sim. Every finding has an on-car heat overlay
 * (Show), a one-sentence "why it matters in iRacing", and a one-click Fix through the REV tools that Ctrl+Z undoes:
 *   - spec / paint corrections are written into the REV-MATERIAL layer (js/rev/material, public state + its own undo
 *     entry format, KIND 'rev-material'), so the real engine renders them and RENDER writes them;
 *   - decal fixes use REV-LAYERMAT (SPBRevLayerMat.assign, one layer-stack undo step);
 *   - a shifted zone mask is snapped back through the zone-mask undo bridge (_spbPushZoneMaskUndoSnapshot).
 * Analysis = js/rev/doctor/doctor-core.js (pure; runs in a Worker). Thresholds + calibration: DESIGN.md in
 * _easy_claude_work/rev_tools/doctor/. Opens from Material > Spec Doctor and Spec Tools > Spec Doctor.
 * Kill switch: window.SPB_REV_DOCTOR_OFF / localStorage SPB_REV_DOCTOR_OFF='1' (nothing is added to the page). */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    function off() {
        if (root.SPB_REV_DOCTOR_OFF) return true;
        try { return root.localStorage.getItem('SPB_REV_DOCTOR_OFF') === '1'; } catch (_) { return false; }
    }
    if (off()) { root.SPBRevDoctor = { off: true }; return; }
    const C = root.SPBDoctorCore;
    if (!C) { root.SPBRevDoctor = { off: true, reason: 'doctor-core.js not loaded' }; return; }

    // Values read from engine.BASE_REGISTRY on 2026-10-10 (cal_render.py -> registry_values.json), never typed from memory.
    const REG = { gloss: [0, 30, 16], satin: [0, 95, 70], matte: [0, 200, 160], metallic: [200, 50, 16] };
    const LIFT_BRIGHT = 200, LIFT_DARK = 64, COAT_GLOSS = 16, LIFT_MAXV = 80;
    const DECAL_ROLES = { 'numbers': 1, 'sponsors': 1, 'decals / logos': 1 };
    const KIND = 'rev-material', TS = 64, TSH = 6, UNDO_MAX = 40;
    const ICON = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2.5v4a3 3 0 0 0 6 0v-4"/><path d="M3 2.5h2M9 2.5h2"/><path d="M7 9.5v1.5a2.5 2.5 0 0 0 5 0V9"/><circle cx="12" cy="7.6" r="1.4"/></svg>';
    const XI = '<svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7"/></svg>';
    const SEV = { high: 'High', medium: 'Medium', tip: 'Tip' };

    const D = { panel: null, list: null, status: null, foot: null, ov: null, ovImg: null, ovKey: null, ovRect: '', raf: 0,
        last: null, input: null, ignored: new Set(), showIgnored: false, busy: false, worker: null, workerBad: false,
        log: [], seq: 0, pos: null, plates: {} };

    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (_) {} }
    function el(tag, attrs, html) {
        const e = doc.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function (k) { if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); });
        if (html != null) e.innerHTML = html;
        return e;
    }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function zonesList() { try { return (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : []; } catch (_) { return []; } }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (_) { return []; } }
    function psdPath() { try { return (typeof _psdPath !== 'undefined' && _psdPath) ? _psdPath : (root._psdPath || null); } catch (_) { return root._psdPath || null; } }
    function apiBase() { try { return (root.ShokkerAPI && root.ShokkerAPI.baseUrl) || ''; } catch (_) { return ''; } }
    function canvasDims() { const pc = doc.getElementById('paintCanvas'); return pc ? [pc.width | 0, pc.height | 0] : [0, 0]; }
    function kick() { try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); } catch (_) {} }

    // ------------------------------------------------------------------ the full-size render (what RENDER writes)
    // The Live Preview runs at <= half size; the Doctor asks the same /preview-render route for scale 1.0 with the canonical
    // serializer (buildServerZonesForRender, which already carries the Material + Layer Material layers).
    async function decodeUrl(u) {
        const b64 = String(u).replace(/^data:[^,]*,/, '');
        const bin = atob(b64), a = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
        if (root.SPBSpecPngPixels && typeof root.SPBSpecPngPixels.decode === 'function') return await root.SPBSpecPngPixels.decode(a.buffer);
        const img = new Image();       // fallback: canvas readback (alpha would be premultiplied; spec alpha is 255 in practice)
        await new Promise(function (res, rej) { img.onload = res; img.onerror = rej; img.src = u; });
        const cv = doc.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight;
        const x = cv.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
        return { width: cv.width, height: cv.height, data: x.getImageData(0, 0, cv.width, cv.height).data };
    }
    async function renderFull() {
        if (typeof root.buildServerZonesForRender !== 'function') throw Error('the render serializer is not loaded - restart Shokker Paint Booth');
        const pf = doc.getElementById('paintFile'), paintFile = pf ? String(pf.value || '').trim() : '';
        const body = { paint_file: paintFile, zones: root.buildServerZonesForRender(zonesList()), seed: 51, preview_scale: 1.0, force_refresh: true, preview_nonce: Date.now() };
        try {
            const ip = (typeof _getActiveImportedSpecMapPath === 'function') ? _getActiveImportedSpecMapPath() : (root.importedSpecMapPath || null);
            if (ip) body.import_spec_map = ip;
        } catch (_) {}
        const psd = psdPath();
        let cv = null;
        try {
            if (!psd && typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
                cv = compositeDecalsForRender();
                if (typeof compositeDecalMaskForRender === 'function') { const m = compositeDecalMaskForRender(); if (m) body.decal_mask_base64 = m; }
                const ds = decalLayers.filter(function (dl) { return dl.visible && dl.specFinish && dl.specFinish !== 'none'; }).map(function (dl) { return { specFinish: dl.specFinish }; });
                if (ds.length) body.decal_spec_finishes = ds;
            }
        } catch (_) { cv = null; }
        if (psd || !cv) cv = (typeof root._nuqPreviewComposite === 'function') ? root._nuqPreviewComposite()
            : ((typeof buildLivePaintCompositeCanvas === 'function') ? buildLivePaintCompositeCanvas() : doc.getElementById('paintCanvas'));
        if (cv && cv.width > 0) { body.paint_image_base64 = cv.toDataURL('image/png'); body.paint_file = psd || paintFile; }
        if (!body.paint_file && !body.paint_image_base64) throw Error('load a car paint first');
        const hold = holdPreviews();
        try {
        for (let attempt = 0; attempt < 5; attempt++) {
            const r = await hold.fetch(apiBase() + '/preview-render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            if (r.status === 429) { await sleep(900 * (attempt + 1)); continue; }
            const d = await r.json();
            if (!d || !d.success) throw Error((d && d.error) || ('render failed (' + r.status + ')'));
            if (!d.paint_preview || !d.spec_preview) throw Error('the render returned no pixels');
            const both = await Promise.all([decodeUrl(d.paint_preview), decodeUrl(d.spec_preview)]);
            const p = both[0], s = both[1];
            if (p.width !== s.width || p.height !== s.height) throw Error('paint and spec sizes differ');
            return { W: p.width, H: p.height, paint: p.data, spec: s.data, ms: d.elapsed_ms || 0 };
        }
        throw Error('the render server stayed busy - try again in a moment');
        } finally { hold.release(); }
    }
    // The server ABORTS an in-flight /preview-render the moment a newer one arrives and returns the zones done so far
    // (server.py _preview_abort -> engine "[ABORT] Preview aborted after i/n zones"), with no flag in the reply. A Live
    // Preview kick during the Doctor's render (every fix kicks one) therefore truncated the Doctor's render: findings
    // vanished and a fix read as "gone" on a half-built car. While the Doctor renders, this page's own /preview-render
    // calls wait (they are sent, in order, right after it), so neither render cuts the other short.
    function holdPreviews() {
        const orig = root.fetch, queue = [];
        let held = true;
        const wrapped = function (u, o) {
            try {
                if (held && String((u && u.url) || u).indexOf('/preview-render') >= 0) {
                    const args = arguments;
                    return new Promise(function (res, rej) { queue.push(function () { orig.apply(root, args).then(res, rej); }); });
                }
            } catch (_) {}
            return orig.apply(root, arguments);
        };
        root.fetch = wrapped;
        return {
            fetch: function (u, o) { return orig.call(root, u, o); },
            release: function () {
                held = false;
                if (root.fetch === wrapped) root.fetch = orig;      // else someone wrapped after us: we stay a pass-through
                const q = queue.splice(0);
                q.forEach(function (go) { try { go(); } catch (_) {} });
                if (!q.length) kick();     // our render may have cut short a Live Preview that was already running: redraw it
            }
        };
    }

    // ------------------------------------------------------------------ inputs: body, decal ownership, authored spec
    async function bodyMask(W, H) {
        try {
            const P = root.SpbProCar;
            if (!P || typeof P.paintableMask !== 'function') return null;
            if (typeof P.ensure === 'function') { try { await Promise.race([P.ensure(false), sleep(4000)]); } catch (_) {} }
            const m = P.paintableMask(false);
            return (m && m.length === W * H) ? m : null;
        } catch (_) { return null; }
    }
    let scratch = null, sctx = null;
    function layerAlpha(ls, i, W, H) {     // layer i drawn alone (identity blend), full sheet -> Uint8 alpha (same footprint REV-LAYERMAT measures)
        if (!scratch) scratch = doc.createElement('canvas');
        if (scratch.width !== W || scratch.height !== H) { scratch.width = W; scratch.height = H; sctx = null; }
        if (!sctx) sctx = scratch.getContext('2d', { willReadFrequently: true });
        const ctx = sctx;
        ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.clearRect(0, 0, W, H);
        const copy = ls.slice();
        const draw = function (c, layer, li) {
            copy[li] = Object.assign({}, layer, { blendMode: 'source-over' });
            const fn = root._drawLayerPixelContent;
            const drew = typeof fn === 'function' ? fn(c, copy, li, null) : false;
            c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
            return drew;
        };
        let res = null;
        try {
            if (typeof root._spbCompositeLayerStack === 'function') res = root._spbCompositeLayerStack(ctx, copy, { includeLayer: function (_l, li) { return li === i; }, identityBlend: true, drawLayer: draw });
            else res = { ok: !!draw(ctx, ls[i], i) };
        } catch (_) { res = null; }
        if (!res || !res.ok) return null;
        const d = ctx.getImageData(0, 0, W, H).data, a = new Uint8Array(W * H);
        let any = 0;
        for (let k = 0, j = 3; k < a.length; k++, j += 4) { a[k] = d[j]; any |= d[j]; }
        return any ? a : null;
    }
    function rolesById() {
        const out = {};
        try { (root.SpbProCar && root.SpbProCar.roles ? root.SpbProCar.roles() : []).forEach(function (r) { out[String(r.id)] = r.role || ''; }); } catch (_) {}
        return out;
    }
    function isGuide(l, role) { return /^\s*(mask|wire)\b/i.test(String((l && l.name) || '')) || /template/i.test(role || ''); }
    function materialOf(l) {
        try { const r = root.SPBRevLayerMat && root.SPBRevLayerMat.get ? root.SPBRevLayerMat.get(l) : null; return r ? (r.preset || r.finishId || r.finish || 'set') : null; } catch (_) { return null; }
    }
    // visible ownership of every numbers / sponsors / decals layer: alpha x transmittance of the visible art above it
    function decalInputs(W, H) {
        const ls = psdLayers(), n = W * H;
        if (!ls.length) return [];
        const roles = rolesById(), out = [];
        let trans = null;
        for (let i = ls.length - 1; i >= 0; i--) {
            const L = ls[i]; if (!L || L.visible === false) continue;
            const role = roles[String(L.id)] || '';
            if (isGuide(L, role)) continue;
            const a = layerAlpha(ls, i, W, H); if (!a) continue;
            if (DECAL_ROLES[role]) {
                const own = new Uint8Array(n);
                for (let j = 0; j < n; j++) own[j] = trans ? Math.round(a[j] * trans[j]) : a[j];
                out.push({ id: L.id, name: L.name || ('Layer ' + L.id), role: role, own: own, material: materialOf(L) });
            }
            if (!trans) { trans = new Float32Array(n); trans.fill(1); }
            for (let j = 0; j < n; j++) if (a[j]) trans[j] *= 1 - a[j] / 255;
        }
        return out;
    }
    // where the spec came from the painter's own values (not a catalogue finish): stricter rules apply there
    function authoredMask(W, H) {
        const n = W * H; let m = null;
        const mark = function (src) { if (!m) m = new Uint8Array(n); if (!src) { m.fill(1); return; } for (let i = 0; i < n; i++) if (src[i]) m[i] = 1; };
        try {
            const ip = (typeof _getActiveImportedSpecMapPath === 'function') ? _getActiveImportedSpecMapPath() : (root.importedSpecMapPath || null);
            if (ip) mark(null);
        } catch (_) {}
        zonesList().forEach(function (z) {
            if (!z || z.muted) return;
            const id = String(z.finish || z.base || '');
            if (id.indexOf('ui_') !== 0 && id.indexOf('mono:ui_') !== 0) return;     // SHOKK DROP import
            mark((z.regionMask && z.regionMask.length === n && z.useRegion !== false) ? z.regionMask : null);
        });
        try {
            const S = root.SPBRevMaterial && root.SPBRevMaterial.state;
            if (S && S.sc && S.W === W && S.H === H && S.lb) {
                const b = S.lb; if (!m) m = new Uint8Array(n);
                for (let y = b[1]; y < b[3]; y++) for (let x = b[0]; x < b[2]; x++) { const i = y * W + x; if (S.sc[i * 3] || S.sc[i * 3 + 1] || S.sc[i * 3 + 2]) m[i] = 1; }
            }
        } catch (_) {}
        return m;
    }
    // The painter's own uploaded spec plates (SHOKK DROP), read verbatim: the engine exports any B 1-15 as 16 (iron rule), so
    // a "B = 8, light clearcoat" in an old Photoshop spec never reaches the TGA as 8 - the Doctor can only see that mistake
    // in the upload itself. foot = where the zone uses the plate minus pixels the Material layer already sets B for.
    async function plateInputs(W, H) {
        const n = W * H, out = [], S = root.SPBRevMaterial && root.SPBRevMaterial.state;
        const seen = {};
        for (const z of zonesList()) {
            if (!z || z.muted) continue;
            const id = String(z.finish || z.base || '').replace(/^mono:/, '');
            if (id.indexOf('ui_') !== 0) continue;
            let px = D.plates[id];
            if (px === undefined) {
                px = null;
                try {
                    const r = await fetch(apiBase() + '/api/user-imports/spec-image/' + encodeURIComponent(id));
                    if (r.ok) {
                        const d = await root.SPBSpecPngPixels.decode(await r.arrayBuffer());
                        px = new Uint8Array(n * 4);
                        for (let y = 0; y < H; y++) { const sy = Math.min(d.height - 1, (y * d.height / H) | 0);
                            for (let x = 0; x < W; x++) { const sx = Math.min(d.width - 1, (x * d.width / W) | 0), a = (sy * d.width + sx) * 4, b = (y * W + x) * 4;
                                px[b] = d.data[a]; px[b + 1] = d.data[a + 1]; px[b + 2] = d.data[a + 2]; px[b + 3] = 255; } }
                    }
                } catch (_) { px = null; }
                D.plates[id] = px;
            }
            if (!px) continue;
            const foot = new Uint8Array(n), rm = (z.regionMask && z.regionMask.length === n && z.useRegion !== false) ? z.regionMask : null;
            for (let i = 0; i < n; i++) foot[i] = (!rm || rm[i]) ? 1 : 0;
            if (S && S.sc && S.W === W && S.H === H) for (let i = 0; i < n; i++) if (S.sc[i * 3 + 2]) foot[i] = 0;
            out.push({ id: id + (seen[id] ? '#' + seen[id] : ''), name: z.name || id, spec: px, foot: foot });
            seen[id] = (seen[id] || 0) + 1;
        }
        return out;
    }

    // ------------------------------------------------------------------ analysis (Worker, main-thread fallback)
    function coreUrl() {
        const s = doc.querySelector('script[src*="rev/doctor/doctor-core.js"]');
        return s ? s.src : null;
    }
    function getWorker() {
        if (D.workerBad) return null;
        if (D.worker) return D.worker;
        const u = coreUrl(); if (!u || typeof Worker === 'undefined' || typeof Blob === 'undefined') return null;
        const src = 'self.importScripts(' + JSON.stringify(u) + ');self.onmessage=function(e){try{var r=self.SPBDoctorCore.analyze(e.data.input,{});' +
            'var t=[];r.findings.forEach(function(f){if(f.heat&&f.heat.buffer)t.push(f.heat.buffer)});self.postMessage({ok:true,r:r},t)}catch(x){self.postMessage({ok:false,err:String(x&&x.message||x)})}};';
        try { D.worker = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' }))); } catch (_) { D.workerBad = true; return null; }
        return D.worker;
    }
    function analyzeAsync(inp) {
        return new Promise(function (resolve, reject) {
            const main = function () { setTimeout(function () { try { resolve(C.analyze(inp, {})); } catch (e) { reject(e); } }, 20); };
            const w = getWorker();
            if (!w) { main(); return; }
            const cp = { W: inp.W, H: inp.H, paint: inp.paint.slice(), spec: inp.spec.slice(), body: inp.body ? inp.body.slice() : null,
                authored: inp.authored ? inp.authored.slice() : null,
                decals: inp.decals.map(function (d) { return { id: d.id, name: d.name, role: d.role, material: d.material, own: d.own.slice() }; }),
                plates: (inp.plates || []).map(function (p) { return { id: p.id, name: p.name, spec: p.spec.slice(), foot: p.foot.slice() }; }) };
            const tr = [cp.paint.buffer, cp.spec.buffer];
            if (cp.body) tr.push(cp.body.buffer); if (cp.authored) tr.push(cp.authored.buffer);
            cp.decals.forEach(function (d) { tr.push(d.own.buffer); });
            cp.plates.forEach(function (p) { tr.push(p.spec.buffer, p.foot.buffer); });
            w.onmessage = function (e) { if (e.data && e.data.ok) resolve(e.data.r); else reject(Error((e.data && e.data.err) || 'analysis failed')); };
            w.onerror = function (e) { if (e && e.preventDefault) e.preventDefault(); D.workerBad = true; D.worker = null; main(); };
            w.postMessage({ input: cp }, tr);
        });
    }

    async function run(opts) {
        opts = opts || {};
        if (D.busy) return D.last;
        D.busy = true;
        const seq = ++D.seq, t0 = performance.now();
        setStatus('Rendering the full-size spec map…', true);
        try {
            const r = await renderFull();
            if (seq !== D.seq) return null;
            const dims = canvasDims(), same = dims[0] === r.W && dims[1] === r.H;
            setStatus('Checking ' + r.W + ' × ' + r.H + ' spec…', true);
            const inp = { W: r.W, H: r.H, paint: r.paint, spec: r.spec, body: same ? await bodyMask(r.W, r.H) : null,
                decals: same ? decalInputs(r.W, r.H) : [], authored: same ? authoredMask(r.W, r.H) : null, plates: [] };
            D.plates = {};
            if (same) inp.plates = await plateInputs(r.W, r.H);
            const res = await analyzeAsync(inp);
            if (seq !== D.seq) return null;
            res.render_ms = r.ms; res.wall_ms = Math.round(performance.now() - t0);
            res.sameSize = same;     // false: the render is not canvas-sized, so car parts / decals / uploads were not checked
            D.input = inp; D.last = res;
            if (D.ovKey && !res.findings.some(function (f) { return f.key === D.ovKey; })) hideHeat();
            else if (D.ovKey) showHeat(D.ovKey, true);
            draw();
            return res;
        } catch (e) {
            setStatus('Spec Doctor could not check this car: ' + esc(e && e.message || e), false, true);
            console.warn('[REV-DOCTOR]', e);
            return null;
        } finally { D.busy = false; syncBusy(); }
    }

    // ------------------------------------------------------------------ fixes
    function matWrite(sp, pp, label) {     // write spec / paint patches into the REV-MATERIAL layer as ONE undo step
        const M = root.SPBRevMaterial;
        if (!M || (M.off && M.off()) || !M.ensure || !M.ensure()) return false;
        const S = M.state, W = S.W, H = S.H, n = W * H;
        if (!sp && !pp) return false;
        if (!S.sv) { S.sv = new Uint8Array(n * 3); S.sc = new Uint8Array(n * 3); S.pv = new Uint8Array(n * 3); S.pc = new Uint8Array(n); }
        const boxes = [sp && sp.bbox, pp && pp.bbox].filter(Boolean);
        const bb = [Math.min.apply(null, boxes.map(function (b) { return b[0]; })), Math.min.apply(null, boxes.map(function (b) { return b[1]; })),
            Math.max.apply(null, boxes.map(function (b) { return b[2]; })), Math.max.apply(null, boxes.map(function (b) { return b[3]; }))];
        const TX = (W + TS - 1) >> TSH, keys = [];
        for (let ty = bb[1] >> TSH; ty <= (bb[3] - 1) >> TSH; ty++) for (let tx = bb[0] >> TSH; tx <= (bb[2] - 1) >> TSH; tx++) keys.push(ty * TX + tx);
        const capture = function (key) {    // the REV-MATERIAL tile snapshot format (coats untouched -> no coat entries)
            const tx = key % TX, ty = (key / TX) | 0, x0 = tx << TSH, y0 = ty << TSH, x1 = Math.min(W, x0 + TS), y1 = Math.min(H, y0 + TS), rw = x1 - x0;
            const s = { coat: {}, sv: new Uint8Array(TS * TS * 3), sc: new Uint8Array(TS * TS * 3), pv: new Uint8Array(TS * TS * 3), pc: new Uint8Array(TS * TS) };
            for (let y = y0; y < y1; y++) {
                const a = y * W + x0, d = (y - y0) * TS;
                s.sv.set(S.sv.subarray(a * 3, (a + rw) * 3), d * 3); s.sc.set(S.sc.subarray(a * 3, (a + rw) * 3), d * 3);
                s.pv.set(S.pv.subarray(a * 3, (a + rw) * 3), d * 3); s.pc.set(S.pc.subarray(a, a + rw), d);
            }
            return s;
        };
        const before = keys.map(capture);
        const hadSpec = S.hasSpec, hadPaint = S.hasPaint;
        if (sp) {
            const bw = sp.bbox[2] - sp.bbox[0];
            for (let y = sp.bbox[1]; y < sp.bbox[3]; y++) for (let x = sp.bbox[0]; x < sp.bbox[2]; x++) {
                const o = (y - sp.bbox[1]) * bw + (x - sp.bbox[0]), i = y * W + x;
                for (let c = 0; c < 3; c++) {
                    const a8 = sp.cov[o * 3 + c]; if (!a8) continue;
                    const k = i * 3 + c, a = a8 / 255, V = sp.val[o * 3 + c];
                    if (a >= 1) { S.sc[k] = 255; S.sv[k] = V; continue; }
                    const oc = S.sc[k] / 255, nc = oc + a * (1 - oc);
                    S.sv[k] = Math.max(0, Math.min(255, Math.round((S.sv[k] * oc * (1 - a) + V * a) / nc))); S.sc[k] = Math.round(nc * 255);
                }
            }
            S.hasSpec = true;
        }
        if (pp) {
            const bw = pp.bbox[2] - pp.bbox[0];
            for (let y = pp.bbox[1]; y < pp.bbox[3]; y++) for (let x = pp.bbox[0]; x < pp.bbox[2]; x++) {
                const o = (y - pp.bbox[1]) * bw + (x - pp.bbox[0]), i = y * W + x, a8 = pp.cov[o];
                if (!a8) continue;
                const a = a8 / 255, oc = S.pc[i] / 255, nc = oc + a * (1 - oc), k0 = oc * (1 - a) / nc, k1 = a / nc;
                for (let c = 0; c < 3; c++) S.pv[i * 3 + c] = Math.max(0, Math.min(255, Math.round(S.pv[i * 3 + c] * k0 + pp.val[o * 3 + c] * k1)));
                S.pc[i] = Math.round(nc * 255);
            }
            S.hasPaint = true;
        }
        S.lb = S.lb ? [Math.min(S.lb[0], bb[0]), Math.min(S.lb[1], bb[1]), Math.max(S.lb[2], bb[2]), Math.max(S.lb[3], bb[3])] : bb.slice();
        const tiles = keys.map(function (k, q) { return [k, before[q], capture(k)]; });
        const entry = { label: label, tiles: tiles, created: null, createdIndex: -1, coats: false, layers: true, box: bb, hadSpec: hadSpec, hadPaint: hadPaint };
        S.undo.push(entry);
        let dropped = false;
        if (S.undo.length > UNDO_MAX) { S.undo.shift(); dropped = true; }
        S.redo.length = 0;
        try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (_) {}
        try { if (dropped && typeof root._discardOldestUndoAction === 'function') root._discardOldestUndoAction(KIND); } catch (_) {}
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (_) {}
        S.layerVer++;
        (S.listeners || []).forEach(function (f) { try { f('end', entry); } catch (_) {} });
        M.changed();
        return true;
    }
    function heatOf(f) { return f && f.heat && f.heat.length === D.input.W * D.input.H ? f.heat : null; }
    function liftMask(heat, paint, W, H) {   // the dark paint under the finding (+3 px rim), never brighter paint next to it
        const P = C._p, n = W * H, m0 = new Uint8Array(n);
        for (let i = 0; i < n; i++) m0[i] = heat[i] ? 1 : 0;
        const g = P.dilate(m0, W, H, 3), out = new Uint8Array(n);
        for (let i = 0, j = 0; i < n; i++, j += 4) if (g[i] && Math.max(paint[j], paint[j + 1], paint[j + 2]) <= LIFT_MAXV) out[i] = 255;
        return out;
    }
    function decalUnion(W, H) {
        const n = W * H, u = new Uint8Array(n);
        (D.input.decals || []).forEach(function (d) { for (let i = 0; i < n; i++) if (d.own[i] >= 128) u[i] = 1; });
        return u;
    }
    function snapZone(f) {
        const inp = D.input, W = inp.W, H = inp.H, n = W * H, dx = f.shift[0], dy = f.shift[1];
        const es = C.edgeMaps({ W: W, H: H, paint: inp.paint, spec: inp.spec }).es, h0 = new Uint8Array(n), heat = heatOf(f);
        for (let i = 0; i < n; i++) h0[i] = heat && heat[i] ? 1 : 0;
        const near = C._p.dilate(h0, W, H, 8);
        for (let i = 0; i < n; i++) if (!near[i]) es[i] = 0;
        let best = 0, bi = -1;
        zonesList().forEach(function (z, i) {
            if (!z || z.muted || !z.regionMask || z.regionMask.length !== n) return;
            const s = C.maskEdgeShiftScore(z.regionMask, W, H, es);
            if (s > best) { best = s; bi = i; }
        });
        if (bi < 0 || best < 0.25) return { ok: false, why: 'no zone mask follows these edges' };
        if (typeof root._spbPushZoneMaskUndoSnapshot !== 'function') return { ok: false, why: 'zone mask history unavailable' };
        const z = zonesList()[bi];
        root._spbPushZoneMaskUndoSnapshot(bi);
        z.regionMask = C.shiftMask(z.regionMask, W, H, dx, dy);
        try { if (typeof root.spbRefreshZoneMaskUI === 'function') root.spbRefreshZoneMaskUI(); else if (typeof renderRegionOverlay === 'function') renderRegionOverlay(); } catch (_) {}
        kick();
        return { ok: true, zone: z.name || ('Zone ' + (bi + 1)), score: +best.toFixed(2) };
    }
    function layerMat(ids, preset) {
        const L = root.SPBRevLayerMat;
        if (!L || typeof L.assign !== 'function' || (L.off && L.off())) return { ok: false, why: 'Layer Materials are switched off' };
        const r = L.assign(ids, { preset: preset });
        return { ok: !!(r && r.ok), changed: r && r.changed };
    }
    function applyFix(f, fixId) {
        const inp = D.input, W = inp.W, H = inp.H, heat = heatOf(f);
        const name = (f.fixes.find(function (x) { return x.id === fixId; }) || {}).label || fixId;
        const label = 'Spec Doctor: ' + name;
        switch (fixId) {
            case 'coat16':
                return { ok: matWrite(C.specSet(inp.spec, heat, W, H, [null, null, COAT_GLOSS]), null, label) };
            case 'lift-bright':
                return { ok: matWrite(null, C.paintLift(inp.paint, C.feather(liftMask(heat, inp.paint, W, H), W, H, 2), W, H, LIFT_BRIGHT), label) };
            case 'dark-chrome': {
                const m = C.feather(liftMask(heat, inp.paint, W, H), W, H, 2);
                return { ok: matWrite(C.specSet(inp.spec, m, W, H, [null, null, COAT_GLOSS]), C.paintLift(inp.paint, m, W, H, LIFT_DARK), label) };
            }
            case 'vinyl-gloss': case 'vinyl-matte':
                return layerMat((f.layers || []).map(function (h) { return h.id; }), fixId === 'vinyl-gloss' ? 'gloss' : 'matte');
            case 'preset-matte-decals': {
                const ids = (inp.decals || []).filter(function (d) { return !d.material; }).map(function (d) { return d.id; });
                if (!ids.length) return { ok: false, why: 'this car has no numbers / sponsors / decal layers' };
                return layerMat(ids, 'matte');
            }
            case 'preset-satin-body': case 'preset-metallic-body': {
                const n = W * H, u = decalUnion(W, H), body = inp.body, m = new Uint8Array(n);
                for (let i = 0; i < n; i++) if ((!body || body[i]) && !u[i]) m[i] = 255;
                return { ok: matWrite(C.specSet(inp.spec, m, W, H, fixId === 'preset-satin-body' ? REG.satin : REG.metallic), null, label) };
            }
            case 'snap-zone': return snapZone(f);
            case 'realign-spec': {
                const n = W * H, m0 = new Uint8Array(n); for (let i = 0; i < n; i++) m0[i] = heat[i] ? 1 : 0;
                const g = C._p.dilate(m0, W, H, 2), m = new Uint8Array(n); for (let i = 0; i < n; i++) if (g[i]) m[i] = 255;
                return { ok: matWrite(C.specShift(inp.spec, m, W, H, f.shift[0], f.shift[1]), null, label) };
            }
            case 'soften': {
                const chans = (f.channels || ['G']).map(function (c) { return c === 'M' ? 0 : 1; });
                return { ok: matWrite(C.specBlur(inp.spec, C.feather(heat, W, H, 6), W, H, chans, 2), null, label) };
            }
        }
        return { ok: false, why: 'unknown fix' };
    }
    function overlapFrac(a, b) {
        if (!a || !b) return 0; let k = 0, h = 0;
        for (let i = 0; i < a.length; i += 3) if (a[i]) { k++; if (b[i]) h++; }
        return k ? h / k : 0;
    }
    async function fix(key, fixId) {
        const f = D.last && D.last.findings.find(function (x) { return x.key === key; });
        if (!f || D.busy) return { ok: false, why: D.busy ? 'busy' : 'no such finding' };
        let r;
        try { r = applyFix(f, fixId) || { ok: false }; } catch (e) { r = { ok: false, why: String(e && e.message || e) }; }
        const rec = { at: Date.now(), key: key, check: f.check, fix: fixId, ok: !!r.ok, why: r.why || null, zone: r.zone || null };
        D.log.push(rec);
        if (!r.ok) { toast('Spec Doctor could not apply that fix' + (r.why ? ': ' + r.why : ''), true); return rec; }
        await sleep(120);
        const res = await run();
        const still = res ? res.findings.filter(function (x) { return x.check === f.check && overlapFrac(heatOf(f), x.heat) > 0.1; }) : [];
        rec.gone = (!!res && res.sameSize !== false) ? !still.length : null;     // null = could not verify (never claim "gone" on a partial check)
        toast(rec.gone ? ('Fixed: ' + f.title + '. Ctrl+Z undoes it.') : rec.gone === null ? ('Applied: ' + f.title + '. Run Check again to confirm. Ctrl+Z undoes it.') : ('Applied, but the check still sees part of it: ' + f.title), rec.gone === false);
        return rec;
    }

    // ------------------------------------------------------------------ "where" in car words
    function whereOf(f, W, H) {
        const regs = (f.regions || []).slice(0, 4), names = [];
        let boxes = null;
        try { const m = root.SpbProCar && root.SpbProCar.map ? root.SpbProCar.map() : null; boxes = m && m.boxes; } catch (_) {}
        regs.forEach(function (r) {
            const fx = r.cx / W, fy = r.cy / H;
            let nm = null, ar = 9;
            if (boxes) Object.keys(boxes).forEach(function (k) {
                const b = boxes[k] && boxes[k].bbox; if (!b) return;
                if (fx >= b[0] && fx <= b[2] && fy >= b[1] && fy <= b[3]) { const a = (b[2] - b[0]) * (b[3] - b[1]); if (a < ar) { ar = a; nm = k; } }
            });
            if (!nm) nm = (fy < 0.34 ? 'top' : fy > 0.66 ? 'bottom' : 'middle') + ' ' + (fx < 0.34 ? 'left' : fx > 0.66 ? 'right' : 'centre') + ' of the sheet';
            if (names.indexOf(nm) < 0) names.push(nm);
        });
        if (f.check === 'decal-chrome' && f.layers) return f.layers.map(function (h) { return h.name; }).join(', ');
        if (f.check === 'flat') return 'the whole car';
        return names.length ? names.join(', ') : 'the whole car';
    }

    // ------------------------------------------------------------------ panel
    function ensurePanel() {
        if (D.panel && D.panel.isConnected) return D.panel;
        const p = el('div', { class: 'spb-doc', id: 'spbDoctorPanel', role: 'dialog', 'aria-label': 'Spec Doctor' });
        p.innerHTML = '<div class="spb-doc-head"><span class="spb-doc-ico">' + ICON + '</span><span class="spb-doc-ttl">Spec Doctor</span>' +
            '<button type="button" class="spb-doc-btn spb-doc-run" data-doc="run" title="Render the full-size spec map and check it">Run Check</button>' +
            '<button type="button" class="spb-doc-x" data-doc="close" aria-label="Close Spec Doctor" title="Close (Esc)">' + XI + '</button></div>' +
            '<div class="spb-doc-status" aria-live="polite"></div><div class="spb-doc-list"></div><div class="spb-doc-foot"></div>';
        doc.body.appendChild(p);
        D.panel = p; D.status = p.querySelector('.spb-doc-status'); D.list = p.querySelector('.spb-doc-list'); D.foot = p.querySelector('.spb-doc-foot');
        p.addEventListener('click', onClick);
        p.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); close(); } });
        const head = p.querySelector('.spb-doc-head');
        head.addEventListener('pointerdown', function (e) {
            if (e.target.closest('button')) return;
            const r = p.getBoundingClientRect(), ox = e.clientX - r.left, oy = e.clientY - r.top;
            const mv = function (ev) { place(ev.clientX - ox, ev.clientY - oy); };
            const up = function () { root.removeEventListener('pointermove', mv); root.removeEventListener('pointerup', up); D.pos = [p.offsetLeft, p.offsetTop]; };
            root.addEventListener('pointermove', mv); root.addEventListener('pointerup', up);
        });
        return p;
    }
    // [REV-DOCTOR 2026-10-10e] the whole panel stays inside the window: top is pulled up so >= 480 px fit (less on a short
    // window), the list scrolls inside the rest, and a window resize re-places it (v1 kept only 120 px on screen and ran
    // 274 px past the bottom at 1920x1080 once the Live Preview moved down; at 1100x800 it also sat past the right edge).
    function place(left, top) {
        const p = D.panel; if (!p) return;
        const w = p.offsetWidth || 336, vw = root.innerWidth, vh = root.innerHeight, minH = Math.min(480, vh - 16);
        const t = Math.max(8, Math.min(vh - minH - 8, Math.round(top)));
        p.style.left = Math.max(8, Math.min(vw - w - 8, Math.round(left))) + 'px';
        p.style.top = t + 'px';
        p.style.maxHeight = Math.max(120, vh - t - 8) + 'px';
    }
    root.addEventListener('resize', function () {
        if (!D.panel || D.panel.style.display === 'none') return;
        const pos = D.pos || defaultPos(); place(pos[0], pos[1]);
    });
    function defaultPos() {     // just left of the Live Preview, so the overlay stays in view
        const sp = doc.getElementById('splitPreview'), r = sp && sp.offsetParent ? sp.getBoundingClientRect() : null, w = D.panel.offsetWidth || 336;
        if (r && r.width > 40) return [r.left - w - 10, r.top + 6];
        return [root.innerWidth - w - 16, 120];
    }
    function open(opts) {
        ensurePanel();
        D.panel.style.display = 'flex';
        const pos = D.pos || defaultPos();
        place(pos[0], pos[1]);
        draw();
        try { D.panel.querySelector('.spb-doc-run').focus({ preventScroll: true }); } catch (_) {}
        if (!(opts && opts.noRun) && !D.last && !D.busy) run();
        return true;
    }
    function close() { if (D.panel) D.panel.style.display = 'none'; hideHeat(); }
    function setStatus(html, busy, bad) {
        ensurePanel();
        D.status.innerHTML = html; D.status.classList.toggle('busy', !!busy); D.status.classList.toggle('bad', !!bad);
        syncBusy();
    }
    function syncBusy() {
        if (!D.panel) return;
        D.panel.classList.toggle('spb-doc-busy', D.busy);
        D.panel.querySelectorAll('button[data-doc="run"],button[data-doc="fix"]').forEach(function (b) { b.disabled = D.busy; });
    }
    function draw() {
        if (!D.panel) return;
        const res = D.last;
        if (!res) { if (!D.busy) setStatus('Checks the full-size spec map (what RENDER writes) for mistakes that look wrong in iRacing.'); D.list.innerHTML = ''; D.foot.innerHTML = ''; return; }
        const W = res.W, H = res.H;
        const vis = res.findings.filter(function (f) { return D.showIgnored || !D.ignored.has(f.key); });
        const nf = res.findings.filter(function (f) { return f.severity !== 'tip' && !D.ignored.has(f.key); }).length;
        const nt = res.findings.filter(function (f) { return f.severity === 'tip' && !D.ignored.has(f.key); }).length;
        const secs = ((res.wall_ms || 0) / 1000).toFixed(1);
        setStatus(nf || nt
            ? ('Checked ' + W + ' × ' + H + ' in ' + secs + ' s: <b>' + nf + (nf === 1 ? ' finding' : ' findings') + '</b>' + (nt ? ', ' + nt + (nt === 1 ? ' tip' : ' tips') : ''))
            : ('Checked ' + W + ' × ' + H + ' in ' + secs + ' s: <b>no spec mistakes found</b>.'));
        D.list.innerHTML = vis.map(function (f) {
            const ign = D.ignored.has(f.key);
            const fixes = (f.fixes || []).map(function (x) {
                return '<button type="button" class="spb-doc-btn spb-doc-fix" data-doc="fix" data-key="' + esc(f.key) + '" data-fix="' + esc(x.id) + '" title="' + esc(x.label) + (x.choice ? ' (applies only when you click it)' : '') + '">' + esc(x.label) + '</button>';
            }).join('');
            return '<div class="spb-doc-card' + (ign ? ' ignored' : '') + (D.ovKey === f.key ? ' showing' : '') + '" data-key="' + esc(f.key) + '" data-sev="' + f.severity + '">' +
                '<div class="spb-doc-r1"><span class="spb-doc-sev" data-sev="' + f.severity + '">' + SEV[f.severity] + '</span><span class="spb-doc-name">' + esc(f.title) + '</span></div>' +
                '<div class="spb-doc-where">' + esc(whereOf(f, W, H)) + (f.check !== 'flat' ? ' · ' + Number(f.area || 0).toLocaleString() + ' px' : '') + '</div>' +
                '<div class="spb-doc-why">' + esc(f.why) + '</div>' +
                '<div class="spb-doc-acts"><button type="button" class="spb-doc-btn" data-doc="show" data-key="' + esc(f.key) + '" aria-pressed="' + (D.ovKey === f.key) + '">' + (D.ovKey === f.key ? 'Hide' : 'Show') + '</button>' + fixes +
                '<button type="button" class="spb-doc-btn spb-doc-ign" data-doc="ignore" data-key="' + esc(f.key) + '">' + (ign ? 'Restore' : 'Ignore') + '</button></div></div>';
        }).join('') || '<div class="spb-doc-clean">Nothing to fix. Matte, satin, gloss, metal and decal specs all read the way iRacing expects.</div>';
        const ni = res.findings.filter(function (f) { return D.ignored.has(f.key); }).length;
        D.foot.innerHTML = (ni ? '<button type="button" class="spb-doc-link" data-doc="ignored">' + (D.showIgnored ? 'Hide' : 'Show') + ' Ignored (' + ni + ')</button>' : '') +
            '<span class="spb-doc-note">Fixes go through Material / Layer Materials / the zone mask; Ctrl+Z undoes each one.</span>';
        syncBusy();
    }
    function onClick(e) {
        const b = e.target.closest && e.target.closest('[data-doc]');
        if (!b) return;
        const a = b.getAttribute('data-doc'), key = b.getAttribute('data-key');
        if (a === 'close') close();
        else if (a === 'run') run();
        else if (a === 'show') { if (D.ovKey === key) hideHeat(); else showHeat(key); draw(); }
        else if (a === 'ignore') { if (D.ignored.has(key)) D.ignored.delete(key); else { D.ignored.add(key); if (D.ovKey === key) hideHeat(); } draw(); }
        else if (a === 'ignored') { D.showIgnored = !D.showIgnored; draw(); }
        else if (a === 'fix') { b.textContent = 'Fixing…'; fix(key, b.getAttribute('data-fix')); }
    }

    // ------------------------------------------------------------------ heat overlay on the Live Preview
    function previewImg() {
        const img = doc.getElementById('livePreviewImg');
        if (img && img.naturalWidth && img.offsetParent) return img;
        return null;
    }
    function contentRect(img) {
        const r = img.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return null;
        const s = Math.min(r.width / img.naturalWidth, r.height / img.naturalHeight), w = img.naturalWidth * s, h = img.naturalHeight * s;
        return { left: r.left + (r.width - w) / 2, top: r.top + (r.height - h) / 2, width: w, height: h };
    }
    function heatBitmap(f, W, H) {
        const S2 = Math.max(1, Math.round(W / 1024)), w = Math.ceil(W / S2), h = Math.ceil(H / S2);
        const cv = doc.createElement('canvas'); cv.width = w; cv.height = h;
        const x = cv.getContext('2d'), id = x.createImageData(w, h), d = id.data, heat = f.heat;
        for (let y = 0; y < h; y++) for (let X = 0; X < w; X++) {
            let on = 0;
            for (let yy = y * S2; yy < Math.min(H, y * S2 + S2) && !on; yy++) for (let xx = X * S2; xx < Math.min(W, X * S2 + S2); xx++) if (heat[yy * W + xx]) { on = 1; break; }
            const o = (y * w + X) * 4;
            if (on) { d[o] = 255; d[o + 1] = 46; d[o + 2] = 196; d[o + 3] = 215; } else { d[o] = 0; d[o + 1] = 0; d[o + 2] = 0; d[o + 3] = 120; }
        }
        x.putImageData(id, 0, 0);
        x.strokeStyle = 'rgba(255,46,196,0.95)'; x.lineWidth = Math.max(2, 3 / S2 * 2);
        (f.regions || []).forEach(function (r) {     // rings so small spots can't hide
            const bw = r.bbox[2] - r.bbox[0], bh = r.bbox[3] - r.bbox[1];
            if (Math.max(bw, bh) > 64) return;
            x.beginPath(); x.arc(r.cx / S2, r.cy / S2, Math.max(10, Math.max(bw, bh) / S2 * 0.9 + 8), 0, Math.PI * 2); x.stroke();
        });
        return cv;
    }
    function showHeat(key, quiet) {
        const f = D.last && D.last.findings.find(function (x) { return x.key === key; });
        if (!f || !f.heat) return false;
        const img = previewImg();
        if (!img) { if (!quiet) toast('Open the Live Preview to see where: Spec Doctor draws on it.', true); return false; }
        const host = img.closest('.preview-inner') || img.parentElement;
        if (!D.ov || !D.ov.isConnected || D.ov.parentNode !== host) {
            if (D.ov && D.ov.parentNode) D.ov.parentNode.removeChild(D.ov);
            D.ov = el('canvas', { class: 'spb-doc-overlay', id: 'spbDoctorOverlay', 'aria-hidden': 'true' });
            host.appendChild(D.ov);
        }
        const bm = heatBitmap(f, D.last.W, D.last.H);
        D.ov.width = bm.width; D.ov.height = bm.height;
        D.ov.getContext('2d').drawImage(bm, 0, 0);
        D.ov.style.display = 'block';
        D.ovKey = key; D.ovRect = '';
        if (!D.raf) D.raf = root.requestAnimationFrame(track);
        return true;
    }
    function track() {
        D.raf = 0;
        if (!D.ovKey || !D.ov || !D.ov.isConnected) return;
        const img = previewImg(), host = D.ov.parentNode;
        if (img && host) {
            const cr = contentRect(img), hr = host.getBoundingClientRect();
            if (cr) {
                const L = Math.round(cr.left - hr.left + host.scrollLeft), T = Math.round(cr.top - hr.top + host.scrollTop), w = Math.round(cr.width), h = Math.round(cr.height);
                const sig = L + ',' + T + ',' + w + ',' + h;
                if (sig !== D.ovRect) { D.ovRect = sig; const s = D.ov.style; s.left = L + 'px'; s.top = T + 'px'; s.width = w + 'px'; s.height = h + 'px'; }
            }
        }
        D.raf = root.requestAnimationFrame(track);
    }
    function hideHeat() {
        D.ovKey = null;
        if (D.raf) { root.cancelAnimationFrame(D.raf); D.raf = 0; }
        if (D.ov) D.ov.style.display = 'none';
    }

    // ------------------------------------------------------------------ entry points: Material menu + Spec Tools menu
    function menuButton() {
        const b = el('button', { type: 'button', class: 'vtool-btn spb-doc-menu', 'data-spb-doctor': '1',
            title: 'Spec Doctor: check the spec map for mistakes that look wrong in iRacing, show where, fix in one click' },
            '<span class="spb-mi-ico spb-doc-mi">' + ICON + '</span> Spec Doctor');
        b.addEventListener('click', function (e) {
            e.preventDefault(); e.stopPropagation();
            const det = b.closest('details'); if (det) det.removeAttribute('open');
            open();
        });
        return b;
    }
    function inject() {
        let done = 0;
        const mat = doc.querySelector('#spbRevMatMenu .spb-tb-pop');
        if (mat) { if (!mat.querySelector('[data-spb-doctor]')) mat.appendChild(menuButton()); done++; }
        const sums = doc.querySelectorAll('details.spb-tb-menu > summary');
        for (let i = 0; i < sums.length; i++) {
            if (!/^\s*Spec Tools/i.test(sums[i].textContent || '')) continue;
            const pop = sums[i].parentNode.querySelector('.spb-tb-pop');
            if (pop) { if (!pop.querySelector('[data-spb-doctor]')) pop.appendChild(menuButton()); done++; }
            break;
        }
        return done >= 2;     // Material menu always; a 'Spec Tools' toolbar menu too when the layout has one
    }
    function init() {
        let tries = 0;
        if (!inject()) { const t = setInterval(function () { if (inject() || ++tries > 60) clearInterval(t); }, 1000); }
        doc.addEventListener('keydown', function (e) { if (e.key === 'Escape' && D.panel && D.panel.style.display !== 'none' && !e.defaultPrevented && D.ovKey) { hideHeat(); draw(); } });
    }

    root.SPBRevDoctor = {
        version: C.version, off: off, open: open, close: close, run: run, fix: fix, show: showHeat, hide: hideHeat,
        ignore: function (key) { D.ignored.add(key); draw(); }, result: function () { return D.last; }, state: D,
        _renderFull: renderFull, _inputs: { bodyMask: bodyMask, decalInputs: decalInputs, authoredMask: authoredMask }, _matWrite: matWrite
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
