/* [SPB-REV-AUTOSPEC 2026-10-10] Spec Autopilot: Material > Auto Spec... proposes a complete, believable spec for the whole car in one click.
 *
 * It READS every layer (pixels, name, car-map role, which car parts it sits on, zones) with js/rev/autospec/autospec-core.js, shows a REVIEW LIST
 * (layer -> proposed material, why, confidence, spec now -> proposed) the painter can edit or exclude, previews it live through the Shine Lens,
 * and on Apply assigns the materials as REV-LAYERMAT Layer Materials in ONE undo step (the same capture-before / push-after pattern Layer
 * Effects uses). The Spec Doctor then runs by itself and the result is shown. Autopilot authors no spec and no paint: it only ASSIGNS existing
 * materials (Layer Materials presets + Foundation finishes, with Keep Art Colour so the artwork never changes) and never touches the zones, the
 * Finish Law or the protected finishes.
 *
 * Style dial: Showroom (glossier, more chrome) <-> Race-Worn (satin / matte / brushed, grain = roughness variation).
 * iRacing spec semantics: R = metallic, G = roughness (0 = mirror), B = clearcoat (0-15 none, 16 = max gloss, 255 = dull).
 * Kill switch: window.SPB_REV_AUTOSPEC_OFF = true / localStorage SPB_REV_AUTOSPEC_OFF = '1' (nothing is added to the page).
 * Public: window.SPBRevAutoSpec { open, close, scan, apply, cancel, setStyle, setMaterial, setInclude, rows, state, off }. */
(function (root) {
    'use strict';
    if (!root || !root.document) return;
    const doc = root.document;
    function off() {
        if (root.SPB_REV_AUTOSPEC_OFF) return true;
        try { return root.localStorage.getItem('SPB_REV_AUTOSPEC_OFF') === '1'; } catch (_) { return false; }
    }
    if (off()) { root.SPBRevAutoSpec = { off: true }; return; }
    const C = root.SPBAutoSpecCore;
    if (!C) { root.SPBRevAutoSpec = { off: true, reason: 'autospec-core.js not loaded' }; return; }
    const TAG = '[REV-AUTOSPEC]';
    const STYLE_DEFAULT = 0.5;
    const ICON = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 13.5l7-7"/><path d="M9 3V1.5M8 2.2h2M12.5 7V5.5M11.7 6.2h1.8M12 11.5v-1.5M11.2 10.7h1.6"/></svg>';
    const XI = '<svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2.5 2.5l7 7M9.5 2.5l-7 7"/></svg>';

    const S = { panel: null, list: null, status: null, doc: null, foot: null, rows: [], skipped: [], style: STYLE_DEFAULT, preview: true, busy: false, seq: 0,
        cap: null, orig: null, committed: 0, lensPrev: null, lensTouched: false, base: null, zoneCustom: false, pos: null, W: 2048, H: 2048,
        doctor: null, timer: 0, baseSpec: null, scanMs: 0, applied: false, autoFix: true, fixLog: [], doctorFirst: null };

    function el(tag, attrs, html) {
        const e = doc.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function (k) { if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); });
        if (html != null) e.innerHTML = html;
        return e;
    }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (_) {} }
    function layers() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (_) { return []; } }
    function zonesList() { try { return (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : []; } catch (_) { return []; } }
    function LM() { const m = root.SPBRevLayerMat; return (m && !(m.off && m.off())) ? m : null; }
    function canvasDims() { const pc = doc.getElementById('paintCanvas'); return pc ? [pc.width | 0, pc.height | 0] : [2048, 2048]; }
    function layerById(id) { const ls = layers(); for (let i = 0; i < ls.length; i++) if (ls[i] && String(ls[i].id) === String(id)) return ls[i]; return null; }
    function rowById(id) { for (let i = 0; i < S.rows.length; i++) if (String(S.rows[i].id) === String(id)) return S.rows[i]; return null; }
    function matName(id) { return (C.MAT[id] && C.MAT[id].name) || id; }
    function vals(o) { return o ? ('M ' + o.m + ' · R ' + o.r + ' · C ' + o.cc) : ''; }

    // ------------------------------------------------------------------ read the car: pixels per layer (same footprint REV-LAYERMAT / the Doctor measure)
    let scratch = null, sctx = null;
    function layerDraw(ls, i, W, H) {       // layer i drawn alone, identity blend, full sheet -> {data (RGBA), cv}
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
        return { data: ctx.getImageData(0, 0, W, H).data, cv: scratch };
    }
    function thumbOf(cv, bbox, W, H) {
        try {
            const tw = 52, th = 36, t = doc.createElement('canvas'); t.width = tw; t.height = th;
            const x = t.getContext('2d');
            for (let yy = 0; yy < th; yy += 8) for (let xx = 0; xx < tw; xx += 8) { x.fillStyle = ((xx + yy) / 8) % 2 ? '#3a3a42' : '#2c2c33'; x.fillRect(xx, yy, 8, 8); }
            const bx = Math.max(0, bbox[0]), by = Math.max(0, bbox[1]), bw = Math.max(1, Math.min(W, bbox[2]) - bx), bh = Math.max(1, Math.min(H, bbox[3]) - by);
            const k = Math.min(tw / bw, th / bh), dw = Math.max(1, bw * k), dh = Math.max(1, bh * k);
            x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
            x.drawImage(cv, bx, by, bw, bh, (tw - dw) / 2, (th - dh) / 2, dw, dh);
            return t.toDataURL('image/png');
        } catch (_) { return null; }
    }
    function rolesById() {
        const out = {};
        try { (root.SpbProCar && root.SpbProCar.roles ? root.SpbProCar.roles() : []).forEach(function (r) { out[String(r.id)] = r.role || ''; }); } catch (_) {}
        return out;
    }
    async function partMasks(W, H) {
        const out = [];
        try {
            const P = root.SpbProCar;
            if (!P || typeof P.maskFor !== 'function') return out;
            if (typeof P.ensure === 'function') { try { await Promise.race([P.ensure(false), sleep(4000)]); } catch (_) {} }
            const names = typeof P.parts === 'function' ? P.parts() : [];
            names.forEach(function (n) {
                try { const m = P.maskFor(n); if (m && m.mask && m.mask.length === W * H) out.push({ name: n, mask: m.mask }); } catch (_) {}
            });
        } catch (_) {}
        return out;
    }
    function zoneInfo() {
        const zs = zonesList().filter(function (z) { return z && !z.muted; });
        const set = zs.filter(function (z) { return !!(z.base || z.finish); });
        const custom = set.filter(function (z) { const id = String(z.base || z.finish).replace(/^mono:/, ''); return !(z.color === 'remaining' && id === 'gloss'); });
        return { custom: custom.length > 0, names: custom.map(function (z) { return z.name || ''; }) };
    }
    function nice(p) { return String(p).replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }

    async function scan(opts) {
        opts = opts || {};
        const seq = ++S.seq, t0 = performance.now();
        S.busy = true; draw();
        try {
            const ls = layers(), dims = canvasDims(), W = dims[0], H = dims[1];
            S.W = W; S.H = H;
            if (!ls.length) { S.rows = []; S.skipped = []; setStatus('This car is a flat image with no layers, so there is nothing to read layer by layer. Use the Spec Brush or the zones for it.', false, true); return null; }
            if (!LM()) { setStatus('Layer Materials is switched off, so Auto Spec cannot assign anything.', false, true); return null; }
            const zi = zoneInfo(); S.zoneCustom = zi.custom;
            setStatus('Reading the layers…', true);
            const masks = await partMasks(W, H);
            const roles = rolesById(), n = W * H, rows = [], skipped = [];
            let trans = null;
            const prev = {}; S.rows.forEach(function (r) { prev[r.id] = r; });
            for (let i = ls.length - 1; i >= 0; i--) {
                const L = ls[i];
                if (!L || L.visible === false) continue;
                const role = roles[String(L.id)] || '', name = L.name || ('Layer ' + L.id);
                const guide = /^template/.test(role) || /^\s*(mask|wire)\b/i.test(name) || C.nameKind(name, role, L.groupName) === 'guide';
                if (guide) { skipped.push({ id: L.id, name: name, why: 'guide' }); continue; }
                setStatus('Reading layer ' + (ls.length - i) + ' of ' + ls.length + ': ' + esc(name), true);
                await sleep(0);
                if (seq !== S.seq) return null;
                const d = layerDraw(ls, i, W, H);
                if (!d) continue;
                const px = d.data, own = new Uint8Array(n);
                if (!trans) { trans = new Float32Array(n); trans.fill(1); }
                let any = 0;
                for (let j = 0, k = 3; j < n; j++, k += 4) {
                    const a = px[k]; if (!a) continue;
                    own[j] = Math.round(a * trans[j]); any |= a;
                    trans[j] *= 1 - a / 255;
                }
                if (!any) continue;
                const f = C.features(px, own, W, H, {});
                if (f.n) C.carbonFor(px, own, W, H, f);
                // car parts this layer's visible pixels sit on
                const parts = {};
                if (masks.length && f.n) {
                    const cnt = new Array(masks.length).fill(0); let tot = 0;
                    for (let y = 0; y < H; y += 4) for (let x = 0; x < W; x += 4) { const j = y * W + x; if (own[j] < 128) continue; tot++; for (let q = 0; q < masks.length; q++) if (masks[q].mask[j]) cnt[q]++; }
                    if (tot) masks.forEach(function (m, q) { if (cnt[q] / tot >= 0.05) parts[m.name] = cnt[q] / tot; });
                }
                const samples = []; for (let y = 0; y < H; y += 3) for (let x = 0; x < W; x += 3) { const j = y * W + x; if (own[j] >= 128) samples.push(j); }
                const ownBits = new Uint8Array((n + 7) >> 3); for (let j = 0; j < n; j++) if (own[j] >= 128) ownBits[j >> 3] |= 1 << (j & 7);      // the layer's visible pixels, bit-packed (proof harness)
                const thumb = f.bbox ? thumbOf(d.cv, f.bbox, W, H) : null;
                const meta = { name: name, role: role, group: L.groupName || '', parts: parts, zoneCustom: S.zoneCustom };
                const a = C.analyze(f, meta, S.style, { zoneCustom: S.zoneCustom });
                const lm = LM(), existing = lm && lm.get ? lm.get(L) : null;
                const pr = prev[L.id];
                const row = { id: L.id, name: name, role: role, group: L.groupName || '', idx: i, f: f, cls: a, kind: a.kind, kindLabel: a.kindLabel, look: a.look, ev: a.ev, conf: a.conf,
                    materialId: a.material, why: a.why, px: f.px, cov: f.cov, parts: parts, thumb: thumb, samples: new Uint32Array(samples),
                    existing: existing, ownBits: ownBits, now: null, after: null, already: false, include: false, userSet: false, userInc: false };
                if (pr && pr.userSet) { row.userSet = true; row.materialId = pr.materialId; row.why = pr.why; }
                if (pr && pr.userInc) { row.userInc = true; row.include = pr.include; }
                rows.push(row);
            }
            rows.reverse();                // top of the layer stack first, like the Layers panel
            skipped.reverse();
            S.rows = rows; S.skipped = skipped; S.scanMs = Math.round(performance.now() - t0);
            rows.forEach(function (r) { refreshRow(r); });
            S.doctor = null;
            return rows;
        } catch (e) {
            console.warn(TAG, e);
            setStatus('Auto Spec could not read this car: ' + esc(e && e.message || e), false, true);
            return null;
        } finally { S.busy = false; syncBusy(); draw(); }
    }

    // ------------------------------------------------------------------ measured spec inside each layer's own pixels
    function measure(row, spec, W) {
        const s = row.samples; if (!s || !s.length || !spec) return null;
        const h = [new Uint32Array(256), new Uint32Array(256), new Uint32Array(256)];
        for (let i = 0; i < s.length; i++) { const j = s[i] * 4; h[0][spec[j]]++; h[1][spec[j + 1]]++; h[2][spec[j + 2]]++; }
        const med = function (hh) { let c = 0; const half = s.length / 2; for (let v = 0; v < 256; v++) { c += hh[v]; if (c >= half) return v; } return 255; };
        return { m: med(h[0]), r: med(h[1]), cc: med(h[2]), n: s.length };
    }
    async function baseline() {
        const D = root.SPBRevDoctor;
        if (!D || typeof D._renderFull !== 'function') return null;
        try {
            const r = await D._renderFull();
            S.baseSpec = r;
            S.rows.forEach(function (row) { row.now = measure(row, r.spec, r.W); refreshRow(row); });
            return r;
        } catch (e) { console.warn(TAG, 'baseline render skipped', e); return null; }
    }

    // ------------------------------------------------------------------ row logic
    function refreshRow(row) {
        const mt = C.MAT[row.materialId] || C.MAT.zones;
        row.mat = mt;
        row.already = !!(row.now && mt.m != null && Math.abs(row.now.m - mt.m) <= 10 && Math.abs(row.now.r - mt.r) <= 10 && Math.abs(row.now.cc - mt.cce) <= 10 && !row.existing);
        if (row.existing && !row.userSet) { row.keep = true; }
        row.unsure = row.conf < 0.6 && row.kind !== 'tiny' && row.kind !== 'guide';
        if (!row.userInc) {
            row.include = mt.id !== 'zones' && !row.existing && !row.already && !row.unsure && row.kind !== 'tiny' && row.kind !== 'guide';
        }
        if (mt.id === 'zones' && !row.existing) row.include = false;
    }
    function repick() {
        S.rows.forEach(function (row) {
            if (!row.userSet) {
                const p = C.pick({ kind: row.kind, what: row.cls.what, look: row.look, name: row.cls.name, trimShare: row.cls.trimShare }, S.style, { zoneCustom: S.zoneCustom });
                row.materialId = p.id; row.why = p.why;
            }
            refreshRow(row);
        });
    }
    function refOf(id) {
        const mt = C.MAT[id]; if (!mt || !mt.ref) return null;
        const r = Object.assign({}, mt.ref);
        if (r.finishId) r.keep = true;             // spec only: the artwork keeps its own colours
        return r;
    }
    function plan() {             // layerId -> ref | null (clear) ; untouched layers are absent
        const out = {};
        S.rows.forEach(function (row) {
            if (!row.include) return;
            if (row.materialId === 'zones') { if (row.existing) out[row.id] = null; return; }
            out[row.id] = refOf(row.materialId);
        });
        return out;
    }

    // ------------------------------------------------------------------ trial / commit / revert (one undo step)
    function capture() {
        try {
            if (typeof _snapshotLayerStack !== 'function') return null;
            return { snapshot: _snapshotLayerStack(), selectedId: (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : null,
                zoneSourceLayers: (typeof _snapshotZoneSourceLayers === 'function') ? _snapshotZoneSourceLayers() : undefined };
        } catch (e) { console.warn(TAG, 'capture failed', e); return null; }
    }
    function setFields(map) {       // map: id -> frozen record | null ; writes only the Layer Material field
        const lm = LM(); if (!lm) return 0;
        let n = 0;
        Object.keys(map).forEach(function (id) {
            const L = layerById(id); if (!L) return;
            const rec = map[id];
            if (rec) L[lm.FIELD] = rec; else delete L[lm.FIELD];
            n++;
        });
        root._spbLayerRev = (root._spbLayerRev | 0) + 1;
        try { if (typeof root.renderLayerPanel === 'function') root.renderLayerPanel(); } catch (_) {}
        try { lm.noticeChange(true); } catch (_) {}
        return n;
    }
    function startTrial() {
        if (S.cap) return true;
        const cap = capture(); if (!cap) return false;
        S.cap = cap; S.orig = {};
        const lm = LM();
        layers().forEach(function (L) { S.orig[L.id] = lm ? (lm.get(L) || null) : null; });
        return true;
    }
    function applyTrial() {
        const lm = LM(); if (!lm) return 0;
        if (!startTrial()) return 0;
        const pl = plan(), map = {};
        S.rows.forEach(function (row) {             // every row's layer is set to either its trial value or its original
            if (Object.prototype.hasOwnProperty.call(pl, row.id)) { const r = pl[row.id]; map[row.id] = r ? lm.normalize(r) : null; }
            else map[row.id] = S.orig[row.id] || null;
        });
        return setFields(map);
    }
    function revertTrial() {
        if (!S.cap || !S.orig) return 0;
        const map = {}; Object.keys(S.orig).forEach(function (id) { map[id] = S.orig[id]; });
        return setFields(map);
    }
    function dirty() {          // does the trial differ from the original?
        const lm = LM(); if (!lm || !S.orig) return false;
        const pl = plan();
        return Object.keys(pl).some(function (id) {
            const want = pl[id] ? lm.normalize(pl[id]) : null, was = S.orig[id] || null;
            return JSON.stringify(want) !== JSON.stringify(was);
        });
    }
    function schedule() {
        if (S.timer) clearTimeout(S.timer);
        S.timer = setTimeout(function () {
            S.timer = 0;
            if (S.preview && !S.busy) { applyTrial(); lensOn(); }
            draw();
        }, 220);
    }
    function lensOn() {
        const L = root.SPBRevLens;
        if (!L || !L.setMode) return;
        if (S.lensPrev == null) S.lensPrev = L.getMode ? L.getMode() : 'off';
        if (L.getMode() === 'off') { L.setMode('full'); S.lensTouched = true; }
    }
    function lensRestore() {
        const L = root.SPBRevLens;
        if (L && L.setMode && S.lensTouched && S.lensPrev != null) { try { L.setMode(S.lensPrev); } catch (_) {} }
        S.lensPrev = null; S.lensTouched = false;
    }

    async function apply() {
        if (S.busy) return null;
        const lm = LM(); if (!lm) return null;
        if (!S.rows.length) return null;
        S.busy = true; syncBusy();
        try {
            if (S.timer) { clearTimeout(S.timer); S.timer = 0; }
            if (!S.cap) startTrial();
            else if (!S.preview) { /* trial was paused: reinstate before committing */ }
            const pl = plan();
            const n = applyTrial();
            const changed = dirty();
            const count = Object.keys(pl).length;
            let committed = false;
            if (changed && S.cap && typeof root._pushCapturedLayerStackUndo === 'function') {
                committed = !!root._pushCapturedLayerStackUndo(S.cap, 'Auto Spec: ' + count + (count === 1 ? ' layer' : ' layers'));
            }
            if (changed && !committed) toast('Auto Spec applied, but the undo step could not be recorded.', true);
            S.cap = null; S.orig = null; S.committed++;
            S.rows.forEach(function (row) { row.existing = lm.get(layerById(row.id)) || null; });
            S.applied = true;
            lensOn(); S.lensPrev = null; S.lensTouched = false;      // an applied spec stays on the lens: closing the panel does not switch it off
            setStatus('Applied ' + count + (count === 1 ? ' layer' : ' layers') + '. Checking the spec with the Spec Doctor…', true);
            draw();
            await sleep(400);
            const res = await runDoctor();
            return { count: count, changed: changed, committed: committed, doctor: res };
        } finally { S.busy = false; syncBusy(); draw(); }
    }
    // The Doctor's fixes Autopilot may run by itself: spec-only ones (they never repaint the artwork and never move a zone mask).
    const AUTO_FIX_OK = ['coat16', 'realign-spec', 'vinyl-gloss'];
    function summarize(r, st) {
        const f = (r && r.findings) || [];
        return { high: f.filter(function (x) { return x.severity === 'high'; }).length, medium: f.filter(function (x) { return x.severity === 'medium'; }).length,
            tip: f.filter(function (x) { return x.severity === 'tip'; }).length, items: f.map(function (x) { return { check: x.check, sev: x.severity, title: x.title }; }), ms: r && r.wall_ms };
    }
    async function runDoctor() {
        const D = root.SPBRevDoctor;
        if (!D || typeof D.run !== 'function') { S.doctor = { skipped: true, why: 'The Spec Doctor is switched off.' }; return S.doctor; }
        S.fixLog = [];
        try {
            let r = await D.run();
            S.doctorFirst = r ? summarize(r) : null;
            let rounds = 0;
            while (S.autoFix && r && rounds < 3 && typeof D.fix === 'function') {
                const highs = (r.findings || []).filter(function (x) { return x.severity === 'high' && x.fixes && x.fixes.length; });
                let f = null, fx = null;
                for (let i = 0; i < highs.length && !fx; i++) { const ok = highs[i].fixes.filter(function (q) { return AUTO_FIX_OK.indexOf(q.id) >= 0; })[0]; if (ok) { f = highs[i]; fx = ok; } }
                if (!fx) break;
                setStatus('The Spec Doctor is fixing: ' + esc(f.title) + '…', true);
                const rec = await D.fix(f.key, fx.id);
                S.fixLog.push({ title: f.title, fix: fx.label, ok: !!(rec && rec.ok), gone: rec ? rec.gone : null });
                r = D.result();
                rounds++;
                if (!rec || !rec.ok) break;
            }
            S.doctor = summarize(r); S.doctor.fixes = S.fixLog.slice();
            const st = D.state && D.state.input;
            if (st && st.spec) S.rows.forEach(function (row) { row.after = measure(row, st.spec, st.W); });
        } catch (e) { S.doctor = { skipped: true, why: 'The Spec Doctor could not run: ' + (e && e.message || e) }; }
        return S.doctor;
    }
    function cancel() {
        if (S.timer) { clearTimeout(S.timer); S.timer = 0; }
        if (S.cap) { revertTrial(); S.cap = null; S.orig = null; }
        lensRestore();
    }

    // ------------------------------------------------------------------ public mutators (the panel and the harness share these)
    function setStyle(v, quiet) { S.style = C.clamp01(Number(v)); repick(); if (!quiet) { schedule(); } draw(); return S.style; }
    function setMaterial(id, mid) {
        const row = rowById(id); if (!row || !C.MAT[mid]) return false;
        row.userSet = true; row.materialId = mid; row.why = mid === 'zones' ? 'You chose to leave this layer to the zones.' : 'You chose ' + matName(mid) + '.';
        row.userInc = true; row.include = mid !== 'zones' || !!row.existing; refreshRow(row); row.include = (mid !== 'zones') || !!row.existing;
        schedule(); draw(); return true;
    }
    function setInclude(id, on) { const row = rowById(id); if (!row) return false; row.userInc = true; row.include = !!on; schedule(); draw(); return true; }

    // ------------------------------------------------------------------ panel
    function ensurePanel() {
        if (S.panel && S.panel.isConnected) return S.panel;
        const p = el('div', { class: 'spb-as', id: 'spbAutoSpecPanel', role: 'dialog', 'aria-label': 'Auto Spec' });
        p.innerHTML = '<div class="spb-as-head"><span class="spb-as-ico">' + ICON + '</span><span class="spb-as-ttl">Auto Spec</span>' +
            '<button type="button" class="spb-as-btn" data-as="rescan" title="Read the layers again">Rescan</button>' +
            '<button type="button" class="spb-as-x" data-as="close" aria-label="Close Auto Spec" title="Close (Esc)">' + XI + '</button></div>' +
            '<div class="spb-as-status" aria-live="polite"></div>' +
            '<div class="spb-as-dial"><span class="spb-as-end">Showroom</span><input type="range" class="spb-as-range" min="0" max="100" step="1" aria-label="Style: Showroom to Race-Worn"><span class="spb-as-end">Race-Worn</span></div>' +
            '<div class="spb-as-list"></div><div class="spb-as-doc"></div>' +
            '<div class="spb-as-foot"><label class="spb-as-prev" title="Show the proposed spec on the Live Preview through the Shine Lens"><input type="checkbox" data-as="preview" checked> Live Preview</label><label class="spb-as-prev" title="After Apply, let the Spec Doctor repair high problems with spec-only fixes (each fix is its own Ctrl+Z step)"><input type="checkbox" data-as="autofix" checked> Doctor fixes</label>' +
            '<span class="spb-as-sp"></span><button type="button" class="spb-as-btn" data-as="cancel">Cancel</button><button type="button" class="spb-as-btn spb-as-go" data-as="apply">Apply Auto Spec</button></div>';
        doc.body.appendChild(p);
        S.panel = p; S.status = p.querySelector('.spb-as-status'); S.list = p.querySelector('.spb-as-list'); S.doc = p.querySelector('.spb-as-doc'); S.foot = p.querySelector('.spb-as-foot');
        p.addEventListener('click', onClick);
        p.addEventListener('change', onChange);
        p.addEventListener('input', onInput);
        p.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); close(); } });
        const head = p.querySelector('.spb-as-head');
        head.addEventListener('pointerdown', function (e) {
            if (e.target.closest('button')) return;
            const r = p.getBoundingClientRect(), ox = e.clientX - r.left, oy = e.clientY - r.top;
            const mv = function (ev) { place(ev.clientX - ox, ev.clientY - oy); };
            const up = function () { root.removeEventListener('pointermove', mv); root.removeEventListener('pointerup', up); S.pos = [p.offsetLeft, p.offsetTop]; };
            root.addEventListener('pointermove', mv); root.addEventListener('pointerup', up);
        });
        return p;
    }
    function place(left, top) {
        const p = S.panel; if (!p) return;
        const w = p.offsetWidth || 440, vw = root.innerWidth, vh = root.innerHeight, minH = Math.min(520, vh - 16);
        const t = Math.max(8, Math.min(vh - minH - 8, Math.round(top)));
        p.style.left = Math.max(8, Math.min(vw - w - 8, Math.round(left))) + 'px';
        p.style.top = t + 'px';
        p.style.maxHeight = Math.max(160, vh - t - 8) + 'px';
    }
    // wait for the page layout to settle after a resize, so the default spot (left of the Live Preview) is measured on the NEW layout
    let resizeT = 0;
    root.addEventListener('resize', function () {
        if (!S.panel || S.panel.style.display === 'none') return;
        place(S.pos ? S.pos[0] : S.panel.offsetLeft, S.pos ? S.pos[1] : S.panel.offsetTop);     // keep it on screen right away
        clearTimeout(resizeT);
        resizeT = setTimeout(function () { if (!S.panel || S.panel.style.display === 'none') return; const pos = S.pos || defaultPos(); place(pos[0], pos[1]); }, 350);
    });
    function defaultPos() {
        const sp = doc.getElementById('splitPreview'), r = sp && sp.offsetParent ? sp.getBoundingClientRect() : null, w = S.panel.offsetWidth || 440;
        if (r && r.width > 40) return [r.left - w - 10, r.top + 6];
        return [root.innerWidth - w - 16, 120];
    }
    async function open(opts) {
        opts = opts || {};
        if (!LM()) { toast('Auto Spec needs Layer Materials, which is switched off.', true); return false; }
        ensurePanel();
        S.panel.style.display = 'flex';
        // a fresh open is a fresh session: a stale "Applied" from an earlier Apply (then closed + Ctrl+Z) must not hide the Apply button
        S.applied = false; S.doctor = null; S.fixLog = []; S.doctorFirst = null;
        const pos = S.pos || defaultPos(); place(pos[0], pos[1]);
        S.panel.querySelector('.spb-as-range').value = String(Math.round(S.style * 100));
        S.panel.querySelector('[data-as="preview"]').checked = S.preview;
        draw();
        if (opts.noScan) return true;
        S.baseSpec = null;
        const rows = await scan();
        if (!rows) return false;
        draw();
        if (opts.noBaseline !== true) {
            setStatus('Measuring the spec the car has now…', true); draw();
            await baseline();
            repick(); draw();
        }
        setStatus('', false);
        if (S.preview && !opts.noTrial) { applyTrial(); lensOn(); }
        draw();
        return true;
    }
    function close() {
        if (S.panel) S.panel.style.display = 'none';
        cancel();
    }
    function setStatus(html, busy, bad) {
        ensurePanel();
        S.status.innerHTML = html; S.status.classList.toggle('busy', !!busy); S.status.classList.toggle('bad', !!bad);
    }
    function syncBusy() {
        if (!S.panel) return;
        S.panel.classList.toggle('spb-as-busy', S.busy);
        S.panel.querySelectorAll('button[data-as="apply"],button[data-as="rescan"],select,.spb-as-range,.spb-as-chk').forEach(function (b) { b.disabled = S.busy; });
    }
    function matOptions(sel) {
        const vin = ['gloss', 'satin', 'matte', 'chrome', 'brushed'], coat = ['gel', 'satin_chrome', 'carbon', 'pearl', 'metallic', 'candy'];
        const o = function (id) { return '<option value="' + id + '"' + (id === sel ? ' selected' : '') + '>' + esc(C.MAT[id].name) + '</option>'; };
        return '<option value="zones"' + (sel === 'zones' ? ' selected' : '') + '>Leave To The Zones</option><optgroup label="Vinyl And Foil">' + vin.map(o).join('') + '</optgroup><optgroup label="Coatings (Keep Your Colours)">' + coat.map(o).join('') + '</optgroup>';
    }
    function pct(v) { return Math.round(v * 100) + '%'; }
    function draw() {
        if (!S.panel) return;
        const rows = S.rows, shown = rows;
        const inc = rows.filter(function (r) { return r.include; });
        const chg = inc.length;
        const same = rows.filter(function (r) { return !r.include && (r.already || r.materialId === 'zones') && r.kind !== 'tiny'; }).length;
        if (!S.busy && rows.length) {
            const bits = [];
            const done = S.applied && !dirtyAfterApply(), cnt = done ? rows.filter(function (r) { return r.existing && r.include; }).length : chg;
            bits.push('<b>' + cnt + (cnt === 1 ? ' layer' : ' layers') + '</b> ' + (done ? 'applied' : 'to change'));
            if (same) bits.push(same + ' already right');
            if (S.skipped.length) bits.push(S.skipped.length + ' template ' + (S.skipped.length === 1 ? 'layer' : 'layers') + ' skipped');
            S.status.classList.remove('busy', 'bad');
            S.status.innerHTML = bits.join(' · ') + ' <span class="spb-as-dim">(read in ' + (S.scanMs / 1000).toFixed(1) + ' s)</span>';
        }
        S.list.innerHTML = shown.map(function (r) {
            const mt = r.mat || C.MAT.zones, dis = r.kind === 'tiny';
            const nowTxt = r.now ? 'Now ' + vals(r.now) : '', tgt = mt.m != null ? 'Proposed ' + vals({ m: mt.m, r: mt.r, cc: mt.cce }) : 'Zones decide';
            const aft = r.after ? '<span class="spb-as-meas" title="Measured in the full-size render inside this layer\'s own pixels">Measured ' + vals(r.after) + '</span>' : '';
            const flag = r.existing && !r.userSet ? '<span class="spb-as-tag">Has a material</span>' : r.already ? '<span class="spb-as-tag">Already right</span>' : r.unsure && !r.userInc ? '<span class="spb-as-tag spb-as-unsure" title="Autopilot is not sure what this layer is, so it is switched off until you tick it">Not sure</span>' : '';
            const parts = Object.keys(r.parts || {}).sort(function (a, b) { return r.parts[b] - r.parts[a]; }).slice(0, 2).map(nice).join(' + ');
            return '<div class="spb-as-row' + (r.include ? ' on' : '') + (dis ? ' dis' : '') + '" data-id="' + esc(r.id) + '">' +
                '<input type="checkbox" class="spb-as-chk" data-as="inc" data-id="' + esc(r.id) + '"' + (r.include ? ' checked' : '') + (dis ? ' disabled' : '') + ' aria-label="Include ' + esc(r.name) + '">' +
                (r.thumb ? '<img class="spb-as-th" alt="" src="' + r.thumb + '">' : '<span class="spb-as-th"></span>') +
                '<div class="spb-as-main"><div class="spb-as-r1"><button type="button" class="spb-as-name" data-as="pick" data-id="' + esc(r.id) + '" title="Select this layer">' + esc(r.name) + '</button>' +
                '<select class="spb-as-sel" data-as="mat" data-id="' + esc(r.id) + '" aria-label="Material for ' + esc(r.name) + '">' + matOptions(r.materialId) + '</select></div>' +
                '<div class="spb-as-r2"><span class="spb-as-kind">' + esc(r.kindLabel) + '</span>' + (parts ? '<span class="spb-as-dim"> · ' + esc(parts) + '</span>' : '') + flag + '<span class="spb-as-conf" title="How sure Autopilot is that it read this layer right">' + pct(r.conf) + '</span></div>' +
                '<div class="spb-as-why">' + esc(r.why) + '</div>' +
                '<div class="spb-as-nums">' + (nowTxt ? esc(nowTxt) + ' → ' : '') + esc(tgt) + (aft ? ' ' + aft : '') + '</div></div></div>';
        }).join('') || '<div class="spb-as-empty">' + (S.busy ? '' : 'No printed layers to read.') + '</div>';
        if (S.skipped.length) S.list.innerHTML += '<div class="spb-as-skip">Not printed, left alone: ' + S.skipped.map(function (s) { return esc(s.name); }).join(', ') + '</div>';
        // Spec Doctor result
        const d = S.doctor;
        if (!d) S.doc.innerHTML = '';
        else if (d.skipped) S.doc.innerHTML = '<span class="spb-as-dim">' + esc(d.why) + '</span>';
        else {
            const fx = (d.fixes || []).filter(function (x) { return x.ok; });
            S.doc.innerHTML = '<span class="spb-as-docl' + (d.high ? ' bad' : ' ok') + '">Spec Doctor: <b>' + d.high + ' high</b> · ' + d.medium + ' medium · ' + d.tip + ' ' + (d.tip === 1 ? 'tip' : 'tips') + '</span> <button type="button" class="spb-as-link" data-as="doctor">Open Spec Doctor</button>' +
                (fx.length ? '<div class="spb-as-dim">Fixed by the Doctor: ' + fx.map(function (x) { return esc(x.title); }).join('; ') + '. Each fix is its own Ctrl+Z step.</div>' : '');
        }
        const go = S.panel.querySelector('[data-as="apply"]'), cn = S.panel.querySelector('[data-as="cancel"]');
        if (go) { go.textContent = S.applied && !dirtyAfterApply() ? 'Applied' : 'Apply Auto Spec'; go.disabled = S.busy || (S.applied && !dirtyAfterApply()); }
        if (cn) cn.textContent = S.applied ? 'Close' : 'Cancel';
        syncBusy();
    }
    function dirtyAfterApply() {
        if (!S.applied) return true;
        const lm = LM(); if (!lm) return false;
        const pl = plan();
        return Object.keys(pl).some(function (id) {
            const want = pl[id] ? lm.normalize(pl[id]) : null, L = layerById(id), was = L ? (lm.get(L) || null) : null;
            return JSON.stringify(want) !== JSON.stringify(was);
        });
    }
    function onClick(e) {
        const b = e.target.closest && e.target.closest('[data-as]');
        if (!b || b.tagName === 'SELECT' || b.tagName === 'INPUT') return;
        const a = b.getAttribute('data-as');
        if (a === 'close') close();
        else if (a === 'cancel') { close(); }
        else if (a === 'rescan') { cancel(); S.applied = false; open({}); }
        else if (a === 'apply') { b.textContent = 'Applying…'; apply(); }
        else if (a === 'pick') { try { if (typeof selectPSDLayer === 'function') selectPSDLayer(b.getAttribute('data-id')); } catch (_) {} }
        else if (a === 'doctor') { try { root.SPBRevDoctor && root.SPBRevDoctor.open({ noRun: true }); } catch (_) {} }
    }
    function onChange(e) {
        const t = e.target, a = t.getAttribute && t.getAttribute('data-as');
        if (a === 'mat') setMaterial(t.getAttribute('data-id'), t.value);
        else if (a === 'inc') setInclude(t.getAttribute('data-id'), t.checked);
        else if (a === 'autofix') { S.autoFix = !!t.checked; }
        else if (a === 'preview') {
            S.preview = !!t.checked;
            if (S.preview) { applyTrial(); lensOn(); } else { revertTrial(); }
            draw();
        }
    }
    function onInput(e) {
        const t = e.target;
        if (t.classList && t.classList.contains('spb-as-range')) { S.applied = false; setStyle(Number(t.value) / 100); }
    }

    // ------------------------------------------------------------------ entry point: Material menu, next to the Spec Doctor
    function menuButton() {
        const b = el('button', { type: 'button', class: 'vtool-btn spb-as-menu', 'data-spb-autospec': '1',
            title: 'Auto Spec: read every layer and propose a believable spec for the whole car, with a live Shine Lens preview' },
            '<span class="spb-mi-ico spb-as-mi">' + ICON + '</span> Auto Spec…');
        b.addEventListener('click', function (e) {
            e.preventDefault(); e.stopPropagation();
            const det = b.closest('details'); if (det) det.removeAttribute('open');
            open();
        });
        return b;
    }
    function pops() {       // the Material menu always; a "Spec Tools" toolbar menu too when the layout has one (same places the Spec Doctor sits)
        const out = [], mat = doc.querySelector('#spbRevMatMenu .spb-tb-pop');
        if (mat) out.push(mat);
        const sums = doc.querySelectorAll('details.spb-tb-menu > summary');
        for (let i = 0; i < sums.length; i++) {
            if (!/^\s*Spec Tools/i.test(sums[i].textContent || '')) continue;
            const pop = sums[i].parentNode.querySelector('.spb-tb-pop');
            if (pop && out.indexOf(pop) < 0) out.push(pop);
            break;
        }
        return out;
    }
    function inject() {
        const ps = pops();
        ps.forEach(function (pop) {
            let me = pop.querySelector('[data-spb-autospec]');
            const dr = pop.querySelector('[data-spb-doctor]');
            if (!me) me = menuButton();
            if (dr) { if (me.previousElementSibling !== dr) dr.parentNode.insertBefore(me, dr.nextSibling); }
            else if (!me.parentNode) pop.appendChild(me);
        });
        return ps.length > 0;
    }
    function init() {
        // the Doctor adds its button a little after the menus exist: keep re-seating ours right after it for ~1 minute
        let n = 0;
        const t = setInterval(function () { inject(); if (++n > 60) clearInterval(t); }, 1000);
        inject();
    }

    root.SPBRevAutoSpec = {
        version: C.VERSION, off: off, open: open, close: close, scan: scan, apply: apply, cancel: cancel, setStyle: setStyle, setMaterial: setMaterial, setInclude: setInclude,
        rows: function () { return S.rows; }, state: S, plan: plan, baseline: baseline, runDoctor: runDoctor, measure: measure, applyTrial: applyTrial, revertTrial: revertTrial
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
