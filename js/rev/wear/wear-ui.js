/* [SPB-REV-WEAR 2026-10-10] Race Wear Studio - UI, layer state, undo, payload, save / open (lane REV-WEAR, Claude).
 *
 * Symmetry menu > "Race Wear…" opens a small panel: pick a LOOK (Showroom, Short-Track Oval, Road Course, Dirt Late Model, Endurance 24 h) and the
 * car is race-worn in one click; a LAPS slider (laps or hours) adds wear monotonically, STRENGTH fades the whole layer, NEW SEED re-rolls the detail,
 * MASK OFF SELECTION keeps wear off a sponsor / number (Lasso / Rectangle / Wand / zone clip), KEEP DECALS CLEAN takes every decal layer's footprint out,
 * HIDE / REMOVE. The wear is ONE layer of its own: an engine post-pass (engine/rev_wear_layer.py) that runs LAST, so it sits on top of decals the way real
 * dirt sits on vinyl, and it writes paint AND spec in lockstep. It never touches the PSD layers, the zones or the source paint, so Remove is total.
 *
 * Pipeline: js/rev/wear/wear-core.js generate() (car space from js/rev/fade/fade-space.js) runs in a Web Worker (the main thread never freezes on a
 * slider; fallback = main thread), generated once per (look, laps, seed) at full strength; strength / mask / decals are applied on top (cheap), then
 * three cropped RGB PNGs (paint colour, spec M/R/CC, aux = paint cov / spec cov / dull delta) ride in the REV-MATERIAL payload as
 * zone[0]._spb_rev_material.wear. RENDER reads the full-resolution bytes (proof: render == engine(base, payload), maxdiff 0); the live preview
 * (<= 0.5 scale) gets a premultiplied 2x2 half-resolution copy of the same layer (4x smaller upload; window.SPB_REV_WEAR_FULL_PREVIEW = full).
 * Undo: SPBUndoExt kind 'rev-wear', snapshots of the layer record (the output is a pure function of the record + car => exact).
 * Save / open: serialize() / restore() (js/features/spb-projects.js field revWear; absent = none).
 * KILL SWITCH: window.SPB_REV_WEAR_OFF = true or localStorage SPB_REV_WEAR_OFF = '1' -> no menu, no payload, nothing saved (engine env SPB_REV_WEAR_OFF=1).
 */
(function (root) {
    'use strict';
    const doc = root.document, KIND = 'rev-wear', UNDO_MAX = 40, TAG = '[REV-WEAR]';
    function WC() { return root.SpbRevWear; }
    function RF() { return root.SpbRevFade; }
    function off() { const w = WC(); return !w || w.off() || !RF(); }
    function toast(msg, bad) { try { if (typeof root.showToast === 'function') root.showToast(msg, !!bad); } catch (e) {} }
    function warn(where, e) { if (root.console) root.console.warn(TAG + ' ' + where, e); }

    // ---------------------------------------------------------------- shared pure functions (also shipped into the worker via toString)
    // full-strength generator output -> strength x keep (decals) x (1 - exclusion), cropped to the generator bbox
    function wearFinish(raw, o) {
        if (!raw || !raw.bbox) return null;
        const W = raw.W, x0 = raw.bbox[0], y0 = raw.bbox[1], w = raw.bbox[2], h = raw.bbox[3], op = Math.max(0, Math.min(1, o.op));
        const pc = new Uint8Array(w * h), sc = new Uint8Array(w * h), dc = new Uint8Array(w * h);
        let nP = 0, nS = 0, bx0 = w, by0 = h, bx1 = -1, by1 = -1;
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const i = (y + y0) * W + x + x0, a = raw.pc[i], b = raw.sc[i], d = raw.dc[i];
                if (!a && !b && !d) continue;
                let lim = op; if (o.keep) lim *= o.keep[i] / 255; if (o.excl) lim *= 1 - o.excl[i] / 255;
                if (lim <= 0) continue;
                const j = y * w + x, p = Math.round(a * lim), s = Math.round(b * lim), q = Math.round(d * lim);
                pc[j] = p; sc[j] = s; dc[j] = q;
                if (p) nP++; if (s) nS++;
                if (p || s || q) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
            }
        }
        return { x0, y0, w, h, pc, sc, dc, nP, nS, tb: bx1 < 0 ? null : [bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1] };
    }
    function wearBlobUrl(b) { return new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = () => rej(fr.error); fr.readAsDataURL(b); }); }
    // finished layer -> three opaque RGB PNGs (no alpha: canvas premultiplication would round spec values) + an RGBA overlay crop
    async function wearEncode(raw, f) {
        if (!f || !f.tb) return null;
        const root = (typeof self !== 'undefined') ? self : globalThis;
        // crop = the tight bbox grown to an EVEN origin and EVEN size, so the half-resolution preview copy below lines up 2x2 with the sheet
        const W = raw.W, X0 = (f.x0 + f.tb[0]) & ~1, Y0 = (f.y0 + f.tb[1]) & ~1;
        let tw = f.x0 + f.tb[0] + f.tb[2] - X0, th = f.y0 + f.tb[1] + f.tb[3] - Y0; tw += tw & 1; th += th & 1;
        const n = tw * th * 4;
        const P = new Uint8ClampedArray(n), S = new Uint8ClampedArray(n), A = new Uint8ClampedArray(n), OV = new Uint8ClampedArray(n);
        for (let y = 0; y < th; y++) {
            const fy = Y0 + y - f.y0;
            for (let x = 0; x < tw; x++) {
                const k = (y * tw + x) * 4, fx = X0 + x - f.x0;
                P[k + 3] = 255; S[k + 3] = 255; A[k + 3] = 255;
                if (fx < 0 || fy < 0 || fx >= f.w || fy >= f.h) continue;
                const i = (Y0 + y) * W + X0 + x, j = fy * f.w + fx, i3 = i * 3;
                const p = f.pc[j], s = f.sc[j];
                if (p) { P[k] = raw.pv[i3]; P[k + 1] = raw.pv[i3 + 1]; P[k + 2] = raw.pv[i3 + 2]; OV[k] = P[k]; OV[k + 1] = P[k + 1]; OV[k + 2] = P[k + 2]; OV[k + 3] = p; }
                if (s) { S[k] = raw.sv[i3]; S[k + 1] = raw.sv[i3 + 1]; S[k + 2] = raw.sv[i3 + 2]; }
                A[k] = p; A[k + 1] = s; A[k + 2] = f.dc[j];
            }
        }
        // [REV-WEAR 2026-10-10] half-resolution copy for the LIVE PREVIEW only (it renders at <= 0.5 scale, LIVE_PREVIEW_MAX_SCALE): premultiplied 2x2
        // average, CC snapped out of 1..15. Measured: a 13.8 MB full payload made previews take 8.7 s round trip on the loaded lane machine (engine part 0.7 s)
        // and hit the 18 s watchdog; the half copy is ~4x smaller. RENDER always gets the full-resolution layer (see payload()).
        const hw = tw >> 1, hh = th >> 1, hn = hw * hh * 4;
        const P2 = new Uint8ClampedArray(hn), S2 = new Uint8ClampedArray(hn), A2 = new Uint8ClampedArray(hn);
        for (let y = 0; y < hh; y++) {
            for (let x = 0; x < hw; x++) {
                let pa = 0, sa = 0, da = 0, p0 = 0, p1 = 0, p2 = 0, s0 = 0, s1 = 0, s2 = 0;
                for (let d = 0; d < 4; d++) {
                    const k = ((2 * y + (d >> 1)) * tw + 2 * x + (d & 1)) * 4, p = A[k], s = A[k + 1];
                    pa += p; sa += s; da += A[k + 2];
                    p0 += P[k] * p; p1 += P[k + 1] * p; p2 += P[k + 2] * p; s0 += S[k] * s; s1 += S[k + 1] * s; s2 += S[k + 2] * s;
                }
                const o = (y * hw + x) * 4;
                A2[o] = Math.round(pa / 4); A2[o + 1] = Math.round(sa / 4); A2[o + 2] = Math.round(da / 4); A2[o + 3] = 255; P2[o + 3] = 255; S2[o + 3] = 255;
                if (pa) { P2[o] = Math.round(p0 / pa); P2[o + 1] = Math.round(p1 / pa); P2[o + 2] = Math.round(p2 / pa); }
                if (sa) { S2[o] = Math.round(s0 / sa); S2[o + 1] = Math.round(s1 / sa); const c = Math.round(s2 / sa); S2[o + 2] = (c >= 1 && c <= 15) ? (c < 8 ? 0 : 16) : c; }
            }
        }
        // [REV-WEAR2 2026-10-10] enc() now returns {url, bytes}: the data URL (inline fallback, same bytes as before) AND the raw PNG bytes (binary upload, no base64 on the wire)
        const enc = async (data, w, h) => {
            const c = new OffscreenCanvas(w, h); c.getContext('2d', { alpha: false }).putImageData(new ImageData(data, w, h), 0, 0);
            // opaque canvas -> Chromium writes RGB PNGs (colour type 2, not RGBA 6): measured 10.0 vs 11.6 MB per dirt layer and faster to encode (q9_alpha.py)
            // PNG by default. Lossless WebP (Chromium encodes quality 1.0 losslessly - verified bit-exact on the ARCA layer) is 34 % smaller (8.9 vs 13.5 MB
            // base64) but measured 6x slower to encode (4.1 s vs 0.6 s per layer in the worker), which costs more than the smaller upload saves: opt-in only
            // (window.SPB_REV_WEAR_WEBP = true; the engine decodes either).
            const blob = await c.convertToBlob(root.SPB_REV_WEAR_WEBP ? { type: 'image/webp', quality: 1 } : { type: 'image/png' });
            return { url: await wearBlobUrl(blob), bytes: new Uint8Array(await blob.arrayBuffer()) };
        };
        // upload container (engine/rev_wear_layer.py parse_container): "RW2\0" | u32 header length | header JSON | PNG pv | PNG sv | PNG aux
        const pack = (res, a, b, c) => {
            const hd = new TextEncoder().encode(JSON.stringify({ v: 2, size: [raw.W, raw.H], bbox: [X0, Y0, tw, th], res, n: [a.bytes.length, b.bytes.length, c.bytes.length] }));
            const out = new Uint8Array(8 + hd.length + a.bytes.length + b.bytes.length + c.bytes.length), dv = new DataView(out.buffer);
            out.set([82, 87, 50, 0], 0); dv.setUint32(4, hd.length, true); out.set(hd, 8);
            let o = 8 + hd.length; [a, b, c].forEach(q => { out.set(q.bytes, o); o += q.bytes.length; });
            return out;
        };
        const pv = await enc(P, tw, th), sv = await enc(S, tw, th), aux = await enc(A, tw, th);
        const hpv = await enc(P2, hw, hh), hsv = await enc(S2, hw, hh), haux = await enc(A2, hw, hh);
        const half = { bbox: [X0, Y0, tw, th], pv: hpv.url, sv: hsv.url, aux: haux.url };
        const bin = { full: pack('full', pv, sv, aux), half: pack('half', hpv, hsv, haux) };
        return { bbox: [X0, Y0, tw, th], pv: pv.url, sv: sv.url, aux: aux.url, half, bin, ov: OV, nP: f.nP, nS: f.nS };
    }
    // the worker side: keeps the car space + the last full-strength generation, answers {t:'run'} with the encoded layer
    function wearWorkerMain() {
        let SP = null, SPID = -1, RAW = null, RAWK = '';
        self.onmessage = async function (e) {
            const m = e.data;
            try {
                if (m.t === 'space') { SP = m.sp; SPID = m.id; RAW = null; RAWK = ''; self.postMessage({ t: 'ok', id: m.id }); return; }
                if (m.t === 'run') {
                    if (!SP || SPID !== m.spid) throw new Error('no car space');
                    let gms = 0;
                    if (!RAW || RAWK !== m.gk) { RAW = self.SpbRevWear.generate(SP, m.rec); RAWK = m.gk; gms = RAW.ms; }
                    const t0 = performance.now(), f = wearFinish(RAW, m.o), out = await wearEncode(RAW, f);
                    const res = out ? Object.assign(out, { gms, ems: Math.round(performance.now() - t0), geo: RAW.geo }) : { empty: true, gms };
                    self.postMessage({ t: 'ok', id: m.id, res }, out ? [out.ov.buffer, out.bin.full.buffer, out.bin.half.buffer] : []); return;
                }
            } catch (err) { self.postMessage({ t: 'err', id: m.id, msg: String((err && err.message) || err) }); }
        };
    }

    // ---------------------------------------------------------------- engine: worker with a main-thread fallback
    const E = { worker: null, bad: false, seq: 0, wait: new Map(), spid: -1, spObj: null, local: { raw: null, gk: '' }, starting: null };
    function plainSpace(sp) {
        const o = {};
        Object.keys(sp).forEach(k => { const v = sp[k]; if (typeof v !== 'function' && k !== 'parts' && k.charAt(0) !== '_') o[k] = v; });
        o.parts = {};
        Object.keys(sp.parts || {}).forEach(n => { const r = sp.parts[n], q = {}; Object.keys(r).forEach(k => { if (typeof r[k] !== 'function' && k.charAt(0) !== '_') q[k] = r[k]; }); o.parts[n] = q; });
        return o;
    }
    async function startWorker() {
        if (E.worker || E.bad) return E.worker;
        if (E.starting) return E.starting;
        E.starting = (async () => {
            try {
                if (typeof Worker !== 'function' || typeof OffscreenCanvas !== 'function' || root.SPB_REV_WEAR_NO_WORKER) throw new Error('no worker');
                const tag = doc.querySelector('script[src*="js/rev/wear/wear-core.js"]');
                if (!tag) throw new Error('core script tag not found');
                const src = await (await fetch(tag.src, { cache: 'force-cache' })).text();
                const body = src + '\n' + wearFinish.toString() + '\n' + wearBlobUrl.toString() + '\n' + wearEncode.toString() + '\n(' + wearWorkerMain.toString() + ')();\n';
                const w = new Worker(URL.createObjectURL(new Blob([body], { type: 'text/javascript' })));
                w.onmessage = e => { const m = e.data, p = E.wait.get(m.id); if (!p) return; E.wait.delete(m.id); if (m.t === 'err') p.rej(new Error(m.msg)); else p.res(m.res); };
                w.onerror = e => { warn('worker error', e && e.message); E.bad = true; E.worker = null; E.wait.forEach(p => p.rej(new Error('worker died'))); E.wait.clear(); };
                E.worker = w; return w;
            } catch (e) { E.bad = true; warn('worker unavailable, using the main thread', e && e.message); return null; }
            finally { E.starting = null; }
        })();
        return E.starting;
    }
    function ask(msg, transfer) { return new Promise((res, rej) => { const id = ++E.seq; msg.id = id; E.wait.set(id, { res, rej }); E.worker.postMessage(msg, transfer || []); }); }
    async function runEngine(sp, job) {
        const w = await startWorker();
        if (w) {
            try {
                if (E.spObj !== sp) { const m = { t: 'space', sp: plainSpace(sp) }; E.spObj = null; await ask(m); E.spid = m.id; E.spObj = sp; }
                return await ask({ t: 'run', spid: E.spid, gk: job.gk, rec: job.rec, o: job.o });
            } catch (e) { warn('worker run failed, falling back', e && e.message); E.bad = true; try { E.worker && E.worker.terminate(); } catch (_) {} E.worker = null; E.spObj = null; }
        }
        // main thread
        let gms = 0;
        if (!E.local.raw || E.local.gk !== job.gk || E.local.sp !== sp) { E.local.raw = WC().generate(sp, job.rec); E.local.gk = job.gk; E.local.sp = sp; gms = E.local.raw.ms; }
        const t0 = performance.now(), f = wearFinish(E.local.raw, job.o), out = await wearEncode(E.local.raw, f);
        return out ? Object.assign(out, { gms, ems: Math.round(performance.now() - t0), geo: E.local.raw.geo }) : { empty: true, gms };
    }

    // ---------------------------------------------------------------- layer state
    // rec: { preset, laps 0..100, seed, op 0..100 (strength), visible, decals (keep decals clean), excl: Uint8Array W*H | null (masked-off area, 0..255) }
    const S = { rec: null, undo: [], redo: [], pay: null, payFor: '', res: null, busy: false, want: null, idle: [], listeners: [], err: '', bin: null, ref: null };

    // ---------------------------------------------------------------- [REV-WEAR2 2026-10-10] upload once, then send a reference
    // Measured before (ARCA dirt 70 laps): every /render carried the 14 MB layer as base64 PNG (17.2 MB body), +1.1 s on a 2.4 s render. Now the finished layer goes to
    // POST /api/rev-wear/layer as binary right after it is generated (while the user looks at the preview); the server decodes it there and /render + /preview-render
    // carry {"rw2": key} (~150 bytes). Anything that goes wrong (route missing, kill switch, server restarted, upload not finished yet) falls back to the inline layer.
    // Kill switch: window.SPB_REV_WEAR2_OFF = true or localStorage SPB_REV_WEAR2_OFF = '1' (server: env SPB_REV_WEAR2_OFF=1).
    function rw2Off() {
        try { if (root.SPB_REV_WEAR2_OFF === true || root.SPB_REV_WEAR2_OFF === '1') return true; return !!(root.localStorage && root.localStorage.getItem('SPB_REV_WEAR2_OFF') === '1'); } catch (e) { return false; }
    }
    function look2Off() {
        try { if (root.SPB_REV_WEAR2_LOOK_OFF === true || root.SPB_REV_WEAR2_LOOK_OFF === '1') return true; return !!(root.localStorage && root.localStorage.getItem('SPB_REV_WEAR2_LOOK_OFF') === '1'); } catch (e) { return false; }
    }
    const RW2 = { bad: 0, seen: new Map(), prev: null };   // bad: failed uploads in a row; seen: key -> time the server last confirmed it
    async function postLayer(bin) {
        try {
            const t0 = performance.now(), r = await (RW2.prev || root.fetch).call(root, '/api/rev-wear/layer', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: bin });
            const j = r && r.ok ? await r.json() : null;
            if (j && j.ok && j.key) { RW2.bad = 0; RW2.seen.set(j.key, Date.now()); return { key: j.key, ms: Math.round(performance.now() - t0), bytes: j.bytes, dec: j.decode_ms }; }
            if (j && j.off) RW2.bad = 9;
        } catch (e) { warn('layer upload failed', e && e.message); }
        RW2.bad++; return null;
    }
    // uploads the current layer's two containers: the half-res preview copy first (the live preview waits for it), the full layer in the background
    async function uploadLayers(token, res) {
        const out = { for: token, full: null, half: null, info: {} };
        S.ref = out; S.bin = res.bin;
        for (const kind of ['half', 'full']) {
            if (S.ref !== out || !res.bin || !res.bin[kind]) return;
            if (RW2.bad >= 3) return;
            const r = await postLayer(res.bin[kind]);
            if (S.ref !== out) return;
            if (r) { out[kind] = r.key; out.info[kind] = r; if (kind === 'half') kick(); }
        }
    }
    function keyKind(key) { const r = S.ref; return r && (r.full === key ? 'full' : (r.half === key ? 'half' : null)); }
    async function ensureHeld(key, strict) {
        if (!strict && Date.now() - (RW2.seen.get(key) || 0) < 45000) return true;
        try {
            const r = await (RW2.prev || root.fetch).call(root, '/api/rev-wear/has?key=' + encodeURIComponent(key)), j = r.ok ? await r.json() : null;
            if (j && j.has) { RW2.seen.set(key, Date.now()); return true; }
        } catch (e) {}
        const kind = keyKind(key), bin = kind && S.bin && S.bin[kind];
        if (!bin) return false;
        const r = await postLayer(bin);
        return !!(r && r.key === key);
    }
    // /render and /preview-render: make sure the server still holds the layer the body names; if it can't be restored, swap the inline layer back in
    function installFetchGuard() {
        const cur = root.fetch;
        if (typeof cur !== 'function' || cur.__spbRevWear2) return;
        RW2.prev = cur;
        const g = async function (input, init) {
            try {
                const url = typeof input === 'string' ? input : ((input && input.url) || '');
                if (init && typeof init.body === 'string' && init.body.indexOf('{"rw2":"') >= 0 && /\/(render|preview-render)(\?|$)/.test(url)) {
                    const m = /\{"rw2":"([0-9a-f]{16,64})"[^{}]*\}/.exec(init.body);
                    if (m) {
                        const ok = await ensureHeld(m[1], /\/render(\?|$)/.test(url));
                        if (!ok) {
                            const kind = keyKind(m[1]), inl = kind === 'half' ? S.payHalf : (kind === 'full' ? S.pay : null);
                            if (inl) { const txt = JSON.stringify(inl); init = Object.assign({}, init, { body: init.body.replace(m[0], () => txt) }); }
                            else warn('layer ' + m[1].slice(0, 8) + ' is gone from the server and not in this page; the render goes out without wear');
                        }
                    }
                }
            } catch (e) { warn('fetch guard', e); }
            return cur.call(this, input, init);
        };
        g.__spbRevWear2 = true;
        ['__spbPerf3'].forEach(f => { if (cur[f]) g[f] = cur[f]; });
        root.fetch = g;
    }
    let panel = null, menuBtn = null, overlay = null, ro = null, dragBefore = null, spaceBusy = false;
    function cloneRec(r) { return r ? { preset: r.preset, laps: r.laps, seed: r.seed, op: r.op, visible: r.visible !== false, decals: !!r.decals, excl: r.excl || null } : null; }
    function exclSig(a) { if (!a) return '0'; if (!a.__sig) { let h = 2166136261 >>> 0; for (let i = 0; i < a.length; i += 61) h = Math.imul(h ^ a[i], 16777619) >>> 0; a.__sig = h.toString(36) + '.' + a.length; } return a.__sig; }
    function recKey(r) { return r ? [r.preset, r.laps, r.seed, r.op, r.decals ? 1 : 0, exclSig(r.excl)].join('|') : ''; }
    function emit(w) { S.listeners.forEach(f => { try { f(w); } catch (e) {} }); }
    async function ensureSpace() {
        const r = RF(); if (!r) return null;
        try { if (root.SpbProCar && root.SpbProCar.ensure) await root.SpbProCar.ensure(false); } catch (e) {}
        return await r.build(false);
    }
    function decalKeep(sp) { try { const F = root.SpbRevFadeUI; return F && typeof F.decalMask === 'function' ? F.decalMask(sp) : null; } catch (e) { return null; } }
    function kick() { try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); } catch (e) {} }
    function whenIdle() { return (!S.busy && !S.want) ? Promise.resolve(S.res) : new Promise(res => S.idle.push(res)); }
    function request() {
        if (!S.rec) { S.pay = null; S.payFor = ''; S.res = null; drawOverlay(); refresh(); kick(); return; }
        S.want = cloneRec(S.rec);
        if (!S.busy) pump();
    }
    async function pump() {
        const rec = S.want; S.want = null;
        if (!rec) { S.busy = false; const q = S.idle.splice(0); q.forEach(f => f(S.res)); refresh(); return; }
        S.busy = true; S.err = ''; refresh();
        let res = null;
        try {
            const sp = await ensureSpace();
            if (!sp) throw new Error('the car could not be measured (load the car and its template first)');
            const look2 = !look2Off();   // [REV-WEAR2] feather + the directional marks; window.SPB_REV_WEAR2_LOOK_OFF / localStorage SPB_REV_WEAR2_LOOK_OFF = '1' = the 2026-10-10 morning look
            const job = { gk: [rec.preset, rec.laps, rec.seed, sp.W, sp.H, look2 ? 'v2' : 'v1'].join('|'), rec: { preset: rec.preset, laps: rec.laps, seed: rec.seed, opacity: 1, look2 },
                o: { op: rec.op / 100, keep: rec.decals ? decalKeep(sp) : null, excl: rec.excl || null } };
            res = await runEngine(sp, job);
            const key = recKey(rec);
            S.ref = null; S.bin = null;
            if (res && !res.empty) { S.pay = { v: 1, size: [sp.W, sp.H], bbox: res.bbox, pv: res.pv, sv: res.sv, aux: res.aux }; S.payHalf = res.half ? Object.assign({ v: 1, size: [sp.W, sp.H], res: 'half' }, res.half) : null; S.payFor = key; }
            else { S.pay = null; S.payHalf = null; S.payFor = key; }
            S.res = res; S.resRec = rec;
            if (res && !res.empty && res.bin && !rw2Off() && RW2.bad < 3) {   // [REV-WEAR2] half copy first (awaited: the preview below then goes by reference), the full layer behind it
                const job2 = uploadLayers(key, res); S.up = job2;
                try { await Promise.race([job2.then(() => 0), new Promise(r => setTimeout(r, 4000))]); } catch (e) {}
            }
        } catch (e) { S.err = String((e && e.message) || e); warn('generate', e); }
        drawOverlay(); kick(); emit('built');
        pump();
    }

    // ---------------------------------------------------------------- undo
    function pushUndo(label, before, after) {
        S.undo.push({ label, before: cloneRec(before), after: cloneRec(after) }); if (S.undo.length > UNDO_MAX) S.undo.shift();
        S.redo.length = 0;
        try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (e) {}
        try { if (typeof root._recordUndoAction === 'function') root._recordUndoAction(KIND); } catch (e) {}
    }
    function setRec(r) { S.rec = cloneRec(r); request(); refresh(); refreshMenu(); emit('changed'); }
    function undo() { const e = S.undo.pop(); if (!e) return false; setRec(e.before); S.redo.push(e); return true; }
    function redo() { const e = S.redo.pop(); if (!e) return false; setRec(e.after); S.undo.push(e); return true; }
    function commit(label, next) { const before = S.rec; pushUndo(label, before, next); setRec(next); }
    function registerUndo() {
        if (!root.SPBUndoExt) return;
        root.SPBUndoExt.register(KIND, {
            hasUndo: () => S.undo.length > 0, hasRedo: () => S.redo.length > 0, undo, redo,
            clearRedo: () => { S.redo.length = 0; }, label: () => { const e = S.undo[S.undo.length - 1]; return e ? e.label : 'Race Wear'; }
        });
    }

    // ---------------------------------------------------------------- overlay on the sheet (only while the panel is open)
    function ensureOverlay() {
        const pc = doc.getElementById('paintCanvas'); if (!pc || !pc.parentNode) return null;
        if (!overlay) { overlay = doc.createElement('canvas'); overlay.id = 'spbRevWearOverlay'; overlay.className = 'spb-wr-overlay'; overlay.setAttribute('aria-hidden', 'true'); }
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
    function panelOpen() { return !!(panel && panel.isConnected && panel.style.display !== 'none'); }
    function drawOverlay() {
        if (!panelOpen()) { if (overlay) overlay.style.display = 'none'; return; }
        const o = ensureOverlay(); if (!o) return;
        const ctx = o.getContext('2d'); ctx.clearRect(0, 0, o.width, o.height);
        const r = S.res;
        if (!S.rec || S.rec.visible === false || !r || r.empty || !r.ov) { o.style.display = 'none'; return; }
        o.style.display = '';
        try { ctx.putImageData(new ImageData(new Uint8ClampedArray(r.ov), r.bbox[2], r.bbox[3]), r.bbox[0], r.bbox[1]); } catch (e) { warn('overlay', e); }
    }

    // ---------------------------------------------------------------- panel
    function ico() { return '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M2 12.5c2.2-1.6 4.4-1.6 6 0s3.8 1.6 6 0"/><circle cx="5" cy="5.2" r="1.6"/><circle cx="10.6" cy="4" r=".8"/><circle cx="12" cy="8" r="1.1"/><circle cx="7.6" cy="8.6" r=".6"/></svg>'; }
    function presets() { const w = WC(); return w ? w.PRESETS : []; }
    function buildPanel() {
        if (panel && panel.isConnected) return panel;
        panel = doc.createElement('div'); panel.id = 'spbWearPanel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Race Wear'); panel.style.display = 'none';
        panel.innerHTML =
            '<div class="spb-wr-ph"><span class="spb-wr-pt">' + ico() + 'Race Wear</span><button type="button" class="spb-wr-x" data-k="close" title="Close (Esc). The wear stays on the car." aria-label="Close">×</button></div>' +
            '<div class="spb-wr-lab">Look</div>' +
            '<div class="spb-wr-looks" role="group" aria-label="Wear look">' + presets().map(p => '<button type="button" data-look="' + p.id + '" title="' + p.tip.replace(/"/g, '&quot;') + '">' + p.name + '</button>').join('') + '</div>' +
            '<div class="spb-wr-tip" data-r="tip"></div>' +
            '<div class="spb-wr-row"><label for="spbWrLaps">Laps</label><input id="spbWrLaps" type="range" min="0" max="100" step="1" data-k="laps"><span class="spb-wr-val" data-r="lapsv"></span></div>' +
            '<div class="spb-wr-row"><label for="spbWrOp">Strength</label><input id="spbWrOp" type="range" min="0" max="100" step="1" data-k="op"><span class="spb-wr-val" data-r="opv"></span></div>' +
            '<div class="spb-wr-row"><label class="spb-wr-chk" title="On: numbers, sponsors, logos and the Car Mandatory layer stay clean. Off (real racing): the dirt goes over everything."><input type="checkbox" data-k="decals"> Keep decals clean</label></div>' +
            '<div class="spb-wr-row spb-wr-btns"><button type="button" data-k="seed" title="Same look, different chips, splats and streaks">New Seed</button><button type="button" data-k="mask" title="Keep the wear off the current selection (Lasso, Rectangle, Magic Wand) or the selected zone\'s Clip To area - e.g. a sponsor">Mask Off Selection</button><button type="button" data-k="unmask" title="Let the wear back onto the masked-off areas">Clear Mask</button></div>' +
            '<div class="spb-wr-row"><button type="button" data-k="hide" aria-pressed="false" title="Hide the wear without losing it">Hide</button><span class="spb-wr-grow"></span><span class="spb-wr-status" data-r="status"></span></div>' +
            '<div class="spb-wr-note" data-r="note"></div>' +
            '<div class="spb-wr-pb"><button type="button" data-k="remove" title="Take the wear layer off the car (Ctrl+Z brings it back)">Remove</button><span class="spb-wr-grow"></span><button type="button" data-k="close" class="spb-wr-primary">Done</button></div>';
        doc.body.appendChild(panel);
        panel.addEventListener('click', onClick);
        panel.addEventListener('input', onInput);
        panel.addEventListener('change', onChange);
        doc.addEventListener('keydown', e => { if (e.key === 'Escape' && panelOpen()) closePanel(); });
        return panel;
    }
    function R(n) { return panel && panel.querySelector('[data-r="' + n + '"]'); }
    function K(n) { return panel && panel.querySelector('[data-k="' + n + '"]'); }
    function placePanel() {
        const a = (menuBtn && menuBtn.isConnected && (menuBtn.closest('details') || menuBtn).getBoundingClientRect()) || { left: 80, bottom: 120 };
        const w = panel.offsetWidth || 320, vw = root.innerWidth || 1200, vh = root.innerHeight || 800;
        panel.style.left = Math.max(8, Math.min(vw - w - 8, a.left)) + 'px';
        panel.style.top = Math.max(8, Math.min(vh - Math.min(panel.offsetHeight || 420, vh - 16) - 8, Math.round(a.bottom + 6))) + 'px';
        panel.style.maxHeight = (vh - 24) + 'px';
    }
    function refresh() {
        if (!panel) return;
        const r = S.rec, W = WC(), on = !!r;
        panel.querySelectorAll('[data-look]').forEach(b => b.setAttribute('aria-pressed', on && b.getAttribute('data-look') === r.preset ? 'true' : 'false'));
        const p = W.preset(on ? r.preset : 'oval');
        R('tip').textContent = on ? p.tip : 'Pick a look: the car is race-worn in one click. Dirt and spray rise behind the wheels, bugs and chips hit the nose and leading edges, rubber sits at door height.';
        const L = K('laps'), O = K('op');
        if (L !== doc.activeElement || !on) L.value = on ? r.laps : 55;
        if (O !== doc.activeElement || !on) O.value = on ? r.op : 100;
        L.disabled = O.disabled = !on;
        R('lapsv').textContent = on ? W.lapsText(r.preset, +L.value) : '';
        R('opv').textContent = on ? Math.round(+O.value) + '%' : '';
        K('decals').checked = on && r.decals; K('decals').disabled = !on;
        ['seed', 'mask', 'hide', 'remove'].forEach(k => { K(k).disabled = !on; });
        K('unmask').disabled = !(on && r.excl);
        K('hide').setAttribute('aria-pressed', on && r.visible === false ? 'true' : 'false');
        K('hide').textContent = on && r.visible === false ? 'Show' : 'Hide';
        R('status').textContent = S.busy ? 'Weathering…' : (S.err ? 'Could not build the wear' : '');
        R('note').textContent = S.err ? S.err : (on && r.excl ? 'Part of the car is masked off.' : '');
    }
    function onClick(e) {
        const b = e.target.closest('button'); if (!b || !panel.contains(b)) return;
        const look = b.getAttribute('data-look'), k = b.getAttribute('data-k');
        if (look) {
            const P = WC().preset(look), r = S.rec;
            if (r && r.preset === look && r.visible !== false) return;
            commit('Race Wear: ' + P.name, { preset: look, laps: P.def, seed: r ? r.seed : 1, op: r ? r.op : 100, visible: true, decals: r ? r.decals : false, excl: r ? r.excl : null });
            return;
        }
        const r = S.rec;
        if (k === 'close') return closePanel();
        if (!r) return;
        if (k === 'seed') commit('Race Wear: new seed', Object.assign(cloneRec(r), { seed: (r.seed * 48271 + 11) % 2147483647 % 100000 + 1 }));
        else if (k === 'hide') commit(r.visible === false ? 'Race Wear: show' : 'Race Wear: hide', Object.assign(cloneRec(r), { visible: r.visible === false }));
        else if (k === 'remove') { commit('Race Wear: remove', null); toast('Race Wear removed (Ctrl+Z brings it back).'); }
        else if (k === 'unmask') commit('Race Wear: clear mask', Object.assign(cloneRec(r), { excl: null }));
        else if (k === 'mask') {
            const sp = RF() && RF().cur(), m = sp ? liveSel(sp.W, sp.H) : null;
            if (!m) { toast('Select the area first (Lasso, Rectangle or Magic Wand), then Mask Off Selection.', true); return; }
            const ex = new Uint8Array(sp.W * sp.H); let any = false;
            for (let i = 0; i < ex.length; i++) { const v = Math.max(m[i], r.excl ? r.excl[i] : 0); ex[i] = v; if (v) any = true; }
            if (!any) { toast('The selection is empty.', true); return; }
            commit('Race Wear: mask off selection', Object.assign(cloneRec(r), { excl: ex }));
        }
    }
    function onInput(e) {
        const k = e.target.getAttribute('data-k'); if (!S.rec || (k !== 'laps' && k !== 'op')) return;
        if (!dragBefore) dragBefore = cloneRec(S.rec);
        S.rec = Object.assign(cloneRec(S.rec), k === 'laps' ? { laps: +e.target.value } : { op: +e.target.value });
        refresh(); clearTimeout(onInput.t); onInput.t = setTimeout(request, 120);   // the worker builds the newest value; the main thread stays free
    }
    function onChange(e) {
        const k = e.target.getAttribute('data-k'); if (!S.rec) return;
        if (k === 'laps' || k === 'op') {
            const before = dragBefore || cloneRec(S.rec); dragBefore = null;
            const after = Object.assign(cloneRec(S.rec), k === 'laps' ? { laps: +e.target.value } : { op: +e.target.value });
            if (before[k] === after[k]) return;
            pushUndo(k === 'laps' ? 'Race Wear: laps' : 'Race Wear: strength', before, after); setRec(after);
        } else if (k === 'decals') commit(e.target.checked ? 'Race Wear: keep decals clean' : 'Race Wear: wear over decals', Object.assign(cloneRec(S.rec), { decals: !!e.target.checked }));
    }
    function liveSel(W, H) {
        try { if (typeof _activeSelectionMask === 'function') { const m = _activeSelectionMask(W, H, true); if (m && m.length === W * H) return m; } } catch (e) { }
        try {
            const zc = root.SPBZoneClip;
            if (zc && !root.SPB_ZONECLIP_OFF && typeof zones !== 'undefined') { const z = zones[selectedZoneIndex]; if (z && zc.enabledFor(z)) { const m = zc.clipFor(z, W, H); if (m && m.length === W * H) return m; } }
        } catch (e) { }
        return null;
    }
    async function openPanel() {
        if (off() || spaceBusy) return false;
        buildPanel(); panel.style.display = ''; refresh(); placePanel();
        spaceBusy = true; R('status').textContent = 'Measuring the car…';
        let sp = null; try { sp = await ensureSpace(); } catch (e) { warn('space', e); }
        spaceBusy = false;
        if (!sp) { closePanel(); toast('Race Wear could not line this car up (load the car and its template first).', true); return false; }
        refresh(); placePanel(); drawOverlay();
        startWorker();
        const first = panel.querySelector('[data-look][aria-pressed="true"]') || panel.querySelector('[data-look]'); if (first) try { first.focus({ preventScroll: true }); } catch (e) {}
        return true;
    }
    function closePanel() { if (panel) panel.style.display = 'none'; if (overlay) overlay.style.display = 'none'; }

    // ---------------------------------------------------------------- menu entry (Symmetry menu, next to the other REV tools)
    const MENU_HTML = '<span class="spb-mi-ico spb-sym-ico">' + ico() + '</span> Race Wear…';
    function ensureMenuBtn() {
        if (off()) { if (menuBtn) menuBtn.style.display = 'none'; return false; }
        const pop = doc.querySelector('#spbSymMenu .spb-tb-pop'); if (!pop) return false;
        if (menuBtn && menuBtn.parentNode === pop) return true;
        menuBtn = doc.createElement('button'); menuBtn.type = 'button'; menuBtn.className = 'vtool-btn'; menuBtn.id = 'spbWearMenuBtn';
        menuBtn.title = 'Race-worn in one click: dirt and spray behind the wheels, bugs and stone chips on the nose, rubber at door height, brake dust, a dulled clear - paint and spec together, on its own layer.';
        menuBtn.innerHTML = MENU_HTML;
        const after = pop.querySelector('#spbFadeMenuBtn');
        if (after && after.parentNode === pop) pop.insertBefore(menuBtn, after.nextSibling); else pop.appendChild(menuBtn);
        menuBtn.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); const d = menuBtn.closest('details'); if (d) d.removeAttribute('open'); openPanel(); });
        refreshMenu(); return true;
    }
    function refreshMenu() { if (!menuBtn) return; menuBtn.innerHTML = MENU_HTML + (S.rec ? ' <span class="spb-wr-cnt">' + (S.rec.visible === false ? 'off' : 'on') + '</span>' : ''); }

    // ---------------------------------------------------------------- payload (rides in the REV-MATERIAL field; engine/rev_wear_layer.py)
    function payload(forPreview) {
        if (off() || !S.rec || S.rec.visible === false || !S.pay || S.payFor !== recKey(S.rec)) return null;
        const half = !!(forPreview && S.payHalf && !window.SPB_REV_WEAR_FULL_PREVIEW), base = half ? S.payHalf : S.pay;
        // [REV-WEAR2] the server holds this exact layer (it computed the key from the bytes): send the reference, not 4-14 MB of base64
        const ref = (!rw2Off() && S.ref && S.ref.for === S.payFor) ? S.ref[half ? 'half' : 'full'] : null;
        if (ref) return { rw2: ref, v: 1, size: base.size, bbox: base.bbox, res: half ? 'half' : 'full' };
        return base;
    }
    // the inline form (data-URL PNGs) of the current layer, whatever the server holds: tests, the fallback, anything that wants the pixels
    function inlinePayload(forPreview) {
        if (off() || !S.rec || S.rec.visible === false || !S.pay || S.payFor !== recKey(S.rec)) return null;
        return (forPreview && S.payHalf && !window.SPB_REV_WEAR_FULL_PREVIEW) ? S.payHalf : S.pay;
    }
    // the live preview renders at <= 0.5 scale: it gets the half-resolution copy. Detected by the caller's name; anything else (RENDER, export) gets full res.
    // Error.stackTraceLimit is 10 by default and the serializer sits under several REV wrappers: measured 2026-10-10, the default limit cut the
    // stack before doPreviewRender and the preview sent the full 16 MB layer. Raise it for this one probe only.
    function fromPreview() {
        const L = Error.stackTraceLimit;
        try { Error.stackTraceLimit = 80; return /\bdoPreviewRender\b/.test(String(new Error().stack || '')); } catch (e) { return false; } finally { Error.stackTraceLimit = L; }
    }
    function wrapSerializer() {
        const cur = root.buildServerZonesForRender;
        if (typeof cur !== 'function') return false;
        if (cur.__spbRevWear) return true;
        const RM = root.SPBRevMaterial, revOn = !!(RM && !(typeof RM.off === 'function' && RM.off()));
        if (revOn && !cur.__spbRevMatOrig) return false;   // REV-MATERIAL rebuilds its field from scratch: let it wrap first so ours sits outside it
        const orig = cur;
        const w = function (zs) {
            const out = orig.apply(this, arguments);
            try {
                if (!Array.isArray(out) || !out.length || typeof zones === 'undefined' || zs !== zones) return out;
                const p = payload(fromPreview()); if (!p) return out;
                const sp = RF() && RF().cur(), lay = out[0]._spb_rev_material || { v: 1, size: p.size || (sp ? [sp.W, sp.H] : [2048, 2048]) };
                lay.wear = p; out[0]._spb_rev_material = lay;
            } catch (e) { warn('payload skipped', e); }
            return out;
        };
        // keep every other wrapper's "already wrapped" check satisfied (the LayerMat / Fade re-wrap loop of 2026-10-10 crashed a page)
        w.__spbRevWear = true;
        ['__spbRevMatOrig', '__spbLayerMat', '__spbRevFade', '__spbRevFadeOrig'].forEach(f => { if (cur[f]) w[f] = cur[f]; });
        root.buildServerZonesForRender = w; return true;
    }

    // ---------------------------------------------------------------- save / open
    function maskPng(a, W, H) {
        const c = doc.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d'), id = x.createImageData(W, H), d = id.data;
        for (let i = 0; i < a.length; i++) { const o = i * 4; d[o] = d[o + 1] = d[o + 2] = a[i]; d[o + 3] = 255; }
        x.putImageData(id, 0, 0); return c.toDataURL('image/png');
    }
    function decodeMask(url, W, H) {
        return new Promise((res, rej) => {
            const im = new Image();
            im.onload = () => { const c = doc.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d'); x.drawImage(im, 0, 0, W, H); const d = x.getImageData(0, 0, W, H).data, a = new Uint8Array(W * H); for (let i = 0; i < a.length; i++) a[i] = d[i * 4]; res(a); };
            im.onerror = () => rej(new Error('the saved wear mask did not decode')); im.src = url;
        });
    }
    function serialize() {
        if (off() || !S.rec) return null;
        const r = S.rec, sp = RF() && RF().cur(), W = sp ? sp.W : 2048, H = sp ? sp.H : 2048;
        return { v: 1, size: [W, H], preset: r.preset, laps: r.laps, seed: r.seed, op: r.op, visible: r.visible !== false, decals: !!r.decals, excl: r.excl ? maskPng(r.excl, W, H) : null };
    }
    async function restore(obj) {
        if (off()) return { ok: true, n: 0 };
        S.undo.length = 0; S.redo.length = 0;
        if (!obj || !obj.preset) { if (S.rec) setRec(null); return { ok: true, n: 0 }; }   // a document without wear clears the previous one's
        try {
            const W = obj.size && obj.size[0], H = obj.size && obj.size[1];
            const excl = obj.excl && W > 0 && H > 0 ? await decodeMask(obj.excl, W, H) : null;
            setRec({ preset: String(obj.preset), laps: +obj.laps || 0, seed: +obj.seed || 1, op: obj.op == null ? 100 : +obj.op, visible: obj.visible !== false, decals: !!obj.decals, excl });
            await whenIdle();
            return S.err ? { ok: false, why: S.err } : { ok: true, n: 1 };
        } catch (e) { return { ok: false, why: String((e && e.message) || e) }; }
    }

    // ---------------------------------------------------------------- programmatic use (tests, the helper, MCP)
    async function apply(opts) {
        const o = opts || {}, P = WC().preset(o.preset || 'oval'), r = S.rec;
        commit('Race Wear: ' + P.name, { preset: P.id, laps: o.laps == null ? P.def : +o.laps, seed: o.seed || (r ? r.seed : 1), op: o.op == null ? (r ? r.op : 100) : +o.op,
            visible: true, decals: o.decals == null ? (r ? r.decals : false) : !!o.decals, excl: r ? r.excl : null });
        await whenIdle(); return S.res;
    }
    async function set(patch) { if (!S.rec) return null; commit('Race Wear', Object.assign(cloneRec(S.rec), patch || {})); await whenIdle(); return S.res; }
    async function remove() { if (!S.rec) return null; commit('Race Wear: remove', null); await whenIdle(); return null; }

    function init() {
        if (off()) return;
        registerUndo();
        root.addEventListener('resize', () => { if (panelOpen()) { placePanel(); syncOverlay(); } });
        wrapSerializer();
        try { installFetchGuard(); } catch (e) { warn('fetch guard not installed', e); }
        let tries = 0;
        const t = setInterval(() => { wrapSerializer(); ensureMenuBtn(); if (++tries > 90) clearInterval(t); }, 700);
        doc.addEventListener('toggle', e => { if (e.target && e.target.id === 'spbSymMenu') ensureMenuBtn(); }, true);
        ensureMenuBtn();
    }

    root.SpbRevWearUI = {
        version: 'wear-ui1.0', off, openPanel, closePanel, apply, set, remove, undo, redo, serialize, restore, whenIdle, payload, inlinePayload,
        state: () => ({ rec: cloneRec(S.rec), busy: S.busy, err: S.err, undo: S.undo.length, redo: S.redo.length, worker: !!E.worker, ref: S.ref ? { full: S.ref.full, half: S.ref.half, info: S.ref.info } : null, rw2Bad: RW2.bad, res: S.res ? { bbox: S.res.bbox, nP: S.res.nP, nS: S.res.nS, gms: S.res.gms, ems: S.res.ems, geo: S.res.geo } : null }),
        uploads: () => S.up || Promise.resolve(), rw2Off, _bins: () => S.bin,
        on: f => S.listeners.push(f)
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(window);
