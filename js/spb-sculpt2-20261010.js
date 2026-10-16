/* [SPB-SCULPT2 2026-10-10] Spec Sculpt, refocused (lane SCULPT-2; audit + verdict: _easy_claude_work/sculpt2/AUDIT.md, VERDICT.md).
 * Owner 10:35: "Is SPEC SCULPT even needed now ... IF there's good use for it then we should just TWEAK it ... make this a fun part
 * of the app that can give something different and bring something cool to the table people will ACTUALLY USE".
 *
 * What it is now: SPEC SCULPT opens INSIDE the Paint Booth, on the car you are painting (the old lab built a spec TGA from a file and
 * deployed it straight to iRacing: the editor never saw it, no undo, no save, a dead end).
 *   1. It reads the paint's main colours on the body (paintCanvas x SpbProCar.paintableMask), and which colours touch which.
 *   2. LOOKS: one click gives the whole car a spec look built from real SPB materials (values = engine.BASE_REGISTRY, taken from
 *      SPBAutoSpecCore.MATERIALS): Pop (every colour sits next to a different sheen), Stealth, Showroom, Chrome Trim, Satin Race.
 *      Every colour chip can be changed by hand (or left to the zones).
 *   3. LIGHT: the Shine Lens studio light comes on while the panel is open; drag the puck (or the car) and watch chrome, satin and
 *      matte react before you render.
 *   4. The result is written into the REV-MATERIAL spec layer (`_spb_rev_material.spec`): spec only, the paint is never touched;
 *      Live Preview, RENDER, Save / Open all use that one code path (engine/rev_material_layer.py, no engine change). The engine's
 *      iron floors are already met by every value we write (CC >= 16, R >= 15 unless M >= 240), so the TGA holds the exact values.
 *   5. UNDO: the look is ONE step ('spec-sculpt') in the app's chronological Ctrl+Z trail (generic SPBUndoExt registry); trying
 *      other looks while the panel is open replaces that step instead of stacking new ones; Cancel steps it back.
 * The classic lab (spec-sculpt.html) stays one click away in the panel footer.
 * Kill switch: window.SPB_SCULPT2_OFF = true or localStorage SPB_SCULPT2_OFF = '1' -> SPEC SCULPT opens the classic lab as before,
 * no menu entry, no panel. */
(function (root) {
    'use strict';
    if (!root || !root.document || root.SPBSculpt2) return;
    const doc = root.document;
    const VERSION = 'sculpt2-20261010j';
    const KIND = 'spec-sculpt';
    const NB = 255;                         // label of a pixel that is not body paint
    const MAXK = 8;

    function off() {
        if (root.SPB_SCULPT2_OFF) return true;
        try { return root.localStorage.getItem('SPB_SCULPT2_OFF') === '1'; } catch (_) { return false; }
    }
    /* [LEFTOVERS-3 2026-10-10] kill switch for the lane's changes here: window.SPB_LO3_OFF, or per item window.SPB_LO3_<n>_OFF (this file: item 1). */
    function lo3off(n) { return !!(root.SPB_LO3_OFF || root['SPB_LO3_' + n + '_OFF']); }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k || 'info'); } catch (_) {} }
    function RM() { const r = root.SPBRevMaterial; return r && typeof r.off === 'function' && !r.off() ? r : null; }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

    // ------------------------------------------------------------------ materials (engine.BASE_REGISTRY values via SPBAutoSpecCore)
    // Fallback = the same numbers SPBAutoSpecCore.MATERIALS carries (checked against BASE_REGISTRY by its lane); used only if it is absent.
    const FALLBACK = [
        { id: 'gel', name: 'Gel Coat Gloss', m: 0, r: 15, cc: 16 }, { id: 'gloss', name: 'Gloss', m: 0, r: 30, cc: 16 },
        { id: 'satin', name: 'Satin', m: 0, r: 95, cc: 70 }, { id: 'matte', name: 'Matte', m: 0, r: 200, cc: 160 },
        { id: 'pearl', name: 'Pearl', m: 100, r: 40, cc: 16 }, { id: 'metallic', name: 'Metallic', m: 200, r: 50, cc: 16 },
        { id: 'candy', name: 'Candy', m: 200, r: 15, cc: 16 }, { id: 'satin_chrome', name: 'Satin Chrome', m: 250, r: 45, cc: 40 },
        { id: 'chrome', name: 'Chrome', m: 255, r: 2, cc: 16 }
    ];
    const ORDER = ['gel', 'gloss', 'satin', 'matte', 'pearl', 'metallic', 'candy', 'satin_chrome', 'chrome'];
    const SHORT = { gel: 'Gel Coat', gloss: 'Gloss', satin: 'Satin', matte: 'Matte', pearl: 'Pearl', metallic: 'Metallic', candy: 'Candy', satin_chrome: 'Satin Chrome', chrome: 'Chrome' };
    const FAMILY = { gel: 'gloss', gloss: 'gloss', satin: 'satin', matte: 'matte', pearl: 'metal', metallic: 'metal', candy: 'metal', satin_chrome: 'chrome', chrome: 'chrome' };
    let MATS = null;
    function mats() {
        if (MATS) return MATS;
        const out = {};
        let src = null;
        try { src = root.SPBAutoSpecCore && root.SPBAutoSpecCore.MATERIALS; } catch (_) { src = null; }
        ORDER.forEach(function (id) {
            let m = null;
            if (src) m = src.find(function (x) { return x.id === id; });
            if (!m) m = FALLBACK.find(function (x) { return x.id === id; });
            // what the engine writes: CC floored to 16, R floored to 15 unless chrome (M >= 240) - so the TGA keeps these exact bytes
            const cc = m.cc < 16 ? 16 : m.cc, r = (m.m < 240 && m.r < 15) ? 15 : m.r;
            out[id] = { id: id, name: SHORT[id] || m.name, m: m.m, r: r, cc: cc, fam: FAMILY[id] };
        });
        MATS = out;
        return out;
    }
    function dist(a, b) { const A = mats()[a], B = mats()[b]; return Math.abs(A.m - B.m) + Math.abs(A.r - B.r) + Math.abs(A.cc - B.cc); }

    // ------------------------------------------------------------------ colour maths
    function lin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
    function lab(r, g, b) {
        const R = lin(r), G = lin(g), B = lin(b);
        const x = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047, y = R * 0.2126 + G * 0.7152 + B * 0.0722, z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883;
        const f = function (t) { return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; };
        const fx = f(x), fy = f(y), fz = f(z);
        return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
    }
    function hex(c) { return '#' + c.map(function (v) { return ('0' + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2); }).join(''); }

    // ------------------------------------------------------------------ 1. read the car: main colours + who touches whom
    async function bodyMask(W, H) {
        try {
            const P = root.SpbProCar;
            if (!P || typeof P.paintableMask !== 'function') return null;
            if (typeof P.ensure === 'function') { try { await Promise.race([P.ensure(false), sleep(4000)]); } catch (_) {} }
            const m = P.paintableMask(false);
            return (m && m.length === W * H) ? m : null;
        } catch (_) { return null; }
    }
    // [SCULPT-2 2026-10-10] Read the paint the RENDER writes, not the editing view: #paintCanvas still carries the guide layers
    // (Wire / Mask / Car Mandatory) that every render leaves out, and the first proof sheet showed the white template mesh
    // baked into M/R/CC as a "white" colour (matte lines all over the car). Use the app's guide-free composite
    // (_nuqPreviewComposite, memoised, no side effects) and stamp the decals on top, as the render does.
    function paintPixels(pc, W, H) {
        let src = pc;
        try {
            if (typeof root._nuqPreviewComposite === 'function') {
                const c = root._nuqPreviewComposite();
                if (c && c.width === W && c.height === H) src = c;
            }
        } catch (_) { src = pc; }
        let hasDecals = false;
        try { hasDecals = typeof drawDecalsOnContext === 'function' && typeof decalLayers !== 'undefined' && Array.isArray(decalLayers) && decalLayers.length > 0; } catch (_) {}
        if (src === pc && !hasDecals) return pc.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, W, H).data;
        const c = doc.createElement('canvas'); c.width = W; c.height = H;
        const x = c.getContext('2d', { willReadFrequently: true });
        x.drawImage(src, 0, 0);
        if (hasDecals) { try { drawDecalsOnContext(x, W, H); } catch (_) {} }
        return x.getImageData(0, 0, W, H).data;
    }
    async function analyse() {
        const pc = doc.getElementById('paintCanvas');
        if (!pc || !pc.width || !pc.height) return null;
        const W = pc.width, H = pc.height, N = W * H;
        const data = paintPixels(pc, W, H);
        const body = await bodyMask(W, H);
        const t0 = performance.now();
        // 15-bit colour histogram of the body pixels
        const hist = new Uint32Array(32768), key = new Uint16Array(N);
        let nb = 0;
        for (let i = 0, p = 0; i < N; i++, p += 4) {
            if ((body && !body[i]) || data[p + 3] < 128) { key[i] = 65535; continue; }
            const k = ((data[p] >> 3) << 10) | ((data[p + 1] >> 3) << 5) | (data[p + 2] >> 3);
            key[i] = k; hist[k]++; nb++;
        }
        if (nb < 1000) return null;
        const bins = [];
        for (let k = 0; k < 32768; k++) if (hist[k]) bins.push(k);
        const nB = bins.length, BL = new Float32Array(nB * 3), BW = new Float32Array(nB);
        for (let j = 0; j < nB; j++) {
            const k = bins[j], L = lab(((k >> 10) & 31) * 8 + 4, ((k >> 5) & 31) * 8 + 4, (k & 31) * 8 + 4);
            BL[j * 3] = L[0]; BL[j * 3 + 1] = L[1]; BL[j * 3 + 2] = L[2]; BW[j] = hist[k];
        }
        // deterministic k-means++ (heaviest bin first, then the bin with the largest weight x distance^2)
        const K0 = Math.min(10, nB), C = [];
        let first = 0; for (let j = 1; j < nB; j++) if (BW[j] > BW[first]) first = j;
        C.push([BL[first * 3], BL[first * 3 + 1], BL[first * 3 + 2]]);
        const md = new Float32Array(nB).fill(1e30);
        while (C.length < K0) {
            const c = C[C.length - 1]; let best = -1, bv = -1;
            for (let j = 0; j < nB; j++) {
                const d = (BL[j * 3] - c[0]) ** 2 + (BL[j * 3 + 1] - c[1]) ** 2 + (BL[j * 3 + 2] - c[2]) ** 2;
                if (d < md[j]) md[j] = d;
                const v = Math.sqrt(BW[j]) * md[j];
                if (v > bv) { bv = v; best = j; }
            }
            if (best < 0 || md[best] < 25) break;
            C.push([BL[best * 3], BL[best * 3 + 1], BL[best * 3 + 2]]);
        }
        const asg = new Int32Array(nB);
        function assignAll(cs) {
            for (let j = 0; j < nB; j++) {
                let bi = 0, bd = 1e30;
                for (let c = 0; c < cs.length; c++) { const d = (BL[j * 3] - cs[c][0]) ** 2 + (BL[j * 3 + 1] - cs[c][1]) ** 2 + (BL[j * 3 + 2] - cs[c][2]) ** 2; if (d < bd) { bd = d; bi = c; } }
                asg[j] = bi;
            }
        }
        function update(cs) {
            const s = cs.map(function () { return [0, 0, 0, 0]; });
            for (let j = 0; j < nB; j++) { const a = s[asg[j]], w = BW[j]; a[0] += BL[j * 3] * w; a[1] += BL[j * 3 + 1] * w; a[2] += BL[j * 3 + 2] * w; a[3] += w; }
            return s.map(function (a, i) { return a[3] ? [a[0] / a[3], a[1] / a[3], a[2] / a[3], a[3]] : [cs[i][0], cs[i][1], cs[i][2], 0]; });
        }
        let cs = C;
        for (let it = 0; it < 12; it++) { assignAll(cs); cs = update(cs); }
        // merge near-identical colours (dE < 10), drop specks (< 0.4 % of the body), keep at most MAXK
        let changed = true;
        while (changed) {
            changed = false;
            cs = cs.filter(function (c) { return c[3] > 0; });
            outer: for (let a = 0; a < cs.length; a++) for (let b = a + 1; b < cs.length; b++) {
                const d = Math.sqrt((cs[a][0] - cs[b][0]) ** 2 + (cs[a][1] - cs[b][1]) ** 2 + (cs[a][2] - cs[b][2]) ** 2);
                if (d < 10) { const w = cs[a][3] + cs[b][3]; cs[a] = [(cs[a][0] * cs[a][3] + cs[b][0] * cs[b][3]) / w, (cs[a][1] * cs[a][3] + cs[b][1] * cs[b][3]) / w, (cs[a][2] * cs[a][3] + cs[b][2] * cs[b][3]) / w, w]; cs.splice(b, 1); changed = true; break outer; }
            }
        }
        cs.sort(function (a, b) { return b[3] - a[3]; });
        cs = cs.filter(function (c, i) { return i === 0 || c[3] >= nb * 0.004; }).slice(0, MAXK);
        assignAll(cs); cs = update(cs); assignAll(cs);
        // per-bin label -> per-pixel label map, per-cluster rgb mean + bbox
        const binLab = new Uint8Array(32768).fill(NB);
        for (let j = 0; j < nB; j++) binLab[bins[j]] = asg[j];
        const K = cs.length, labels = new Uint8Array(N).fill(NB);
        const sum = new Float64Array(K * 4), box = []; for (let c = 0; c < K; c++) box.push([W, H, 0, 0]);
        for (let y = 0, i = 0, p = 0; y < H; y++) {
            for (let x = 0; x < W; x++, i++, p += 4) {
                const k = key[i]; if (k === 65535) continue;
                const l = binLab[k]; labels[i] = l;
                const s = l * 4; sum[s] += data[p]; sum[s + 1] += data[p + 1]; sum[s + 2] += data[p + 2]; sum[s + 3]++;
                const b = box[l]; if (x < b[0]) b[0] = x; if (y < b[1]) b[1] = y; if (x >= b[2]) b[2] = x + 1; if (y >= b[3]) b[3] = y + 1;
            }
        }
        // adjacency: label changes between 4-neighbours that are both body paint. "soft" = the two pixels are nearly the same
        // colour (a smooth fade that k-means cut into bands), "hard" = a real design edge.
        const adj = new Float64Array(K * K), soft = new Float64Array(K * K), SOFT = 40;
        const pxd = function (i, j) { const p = i * 4, q = j * 4; return Math.abs(data[p] - data[q]) + Math.abs(data[p + 1] - data[q + 1]) + Math.abs(data[p + 2] - data[q + 2]); };
        for (let y = 0; y < H; y++) {
            const r0 = y * W;
            for (let x = 0; x < W; x++) {
                const i = r0 + x, a = labels[i]; if (a === NB) continue;
                if (x + 1 < W) { const b = labels[i + 1]; if (b !== NB && b !== a) { adj[a * K + b]++; adj[b * K + a]++; if (pxd(i, i + 1) < SOFT) { soft[a * K + b]++; soft[b * K + a]++; } } }
                if (y + 1 < H) { const b = labels[i + W]; if (b !== NB && b !== a) { adj[a * K + b]++; adj[b * K + a]++; if (pxd(i, i + W) < SOFT) { soft[a * K + b]++; soft[b * K + a]++; } } }
            }
        }
        const raw = cs.map(function (c, i) {
            const n = sum[i * 4 + 3] || 1;
            return { rgb: [sum[i * 4] / n, sum[i * 4 + 1] / n, sum[i * 4 + 2] / n], L: c[0], C: Math.sqrt(c[1] * c[1] + c[2] * c[2]), h: Math.atan2(c[2], c[1]), px: sum[i * 4 + 3] };
        });
        // [SCULPT-2 2026-10-10] BLENDS. The ARCA proof sheet showed Pop cutting a rainbow fade into hard candy / matte bands at
        // arbitrary k-means borders. Colours whose shared border is mostly soft are ONE fade, so they become one colour row
        // ("blend") and always get one material: a look never puts a material seam across a smooth fade.
        const par = []; for (let c = 0; c < K; c++) par.push(c);
        const find = function (c) { while (par[c] !== c) { par[c] = par[par[c]]; c = par[c]; } return c; };
        for (let a = 0; a < K; a++) for (let b = a + 1; b < K; b++) {
            // two colours (C >= 12): a fade when >= 25 % of their border is soft (ARCA rainbow: 28-71 %; hard design edges: 0-8 %).
            // a black / white / grey in the pair needs >= 75 %: dark AA shading round a colour reached 54 % on ARCA and must not merge.
            const t = adj[a * K + b], need = (raw[a].C < 12 || raw[b].C < 12) ? 0.75 : 0.25;
            if (t >= 64 && soft[a * K + b] / t >= need) { const ra = find(a), rb = find(b); if (ra !== rb) par[rb] = ra; }
        }
        const gl = [], seen = {};
        for (let c = 0; c < K; c++) { const r = find(c); if (!(r in seen)) { seen[r] = gl.length; gl.push([]); } gl[seen[r]].push(c); }
        const gpx = gl.map(function (m) { return m.reduce(function (s2, c) { return s2 + raw[c].px; }, 0); });
        const order = gl.map(function (_, g) { return g; }).sort(function (x, y) { return gpx[y] - gpx[x]; });   // index 0 = the body
        const map = new Uint8Array(256).fill(NB);
        order.forEach(function (g, ng) { gl[g].forEach(function (c) { map[c] = ng; }); });
        const G = order.length;
        if (G < K) for (let i = 0; i < N; i++) { const l = labels[i]; if (l !== NB) labels[i] = map[l]; }
        const gadj = new Float64Array(G * G);
        for (let x = 0; x < K; x++) for (let y = 0; y < K; y++) { const gx = map[x], gy = map[y]; if (gx !== gy) gadj[gx * G + gy] += adj[x * K + y]; }
        const cl = order.map(function (g, ng) {
            const m = gl[g].slice().sort(function (x, y) { return raw[y].px - raw[x].px; }), px = gpx[g] || 1;
            let r = 0, gg = 0, bb = 0, L = 0, Cc = 0; const bx = [W, H, 0, 0];
            m.forEach(function (c) {
                const w = raw[c].px / px, q = raw[c].rgb, b2 = box[c];
                r += q[0] * w; gg += q[1] * w; bb += q[2] * w; L += raw[c].L * w; Cc += raw[c].C * w;
                if (b2[2] > b2[0]) { bx[0] = Math.min(bx[0], b2[0]); bx[1] = Math.min(bx[1], b2[1]); bx[2] = Math.max(bx[2], b2[2]); bx[3] = Math.max(bx[3], b2[3]); }
            });
            let per = 0; for (let j = 0; j < G; j++) per += gadj[ng * G + j];
            const blend = m.length > 1 ? m.slice().sort(function (x, y) { return raw[x].h - raw[y].h; }).map(function (c) { return hex(raw[c].rgb); }) : null;
            return { i: ng, rgb: m.length > 1 ? raw[m[0]].rgb : [r, gg, bb], hex: hex(m.length > 1 ? raw[m[0]].rgb : [r, gg, bb]), L: L, C: Cc, px: gpx[g], share: gpx[g] / nb, per: per, thin: per / Math.max(1, gpx[g]), box: bx, blend: blend };
        });
        const pairs = [];   // diagnostics: raw colour pairs, border length, % soft border (blend rule above)
        for (let x = 0; x < K; x++) for (let y = x + 1; y < K; y++) { const t = adj[x * K + y]; if (t) pairs.push([hex(raw[x].rgb), hex(raw[y].rgb), t, Math.round(100 * soft[x * K + y] / t)]); }
        return { W: W, H: H, N: N, nb: nb, K: G, kRaw: K, pairs: pairs, labels: labels, adj: gadj, cl: cl, bodyMask: !!body, ms: Math.round(performance.now() - t0), paintSig: sig(data) };
    }
    function sig(d) { let h = 0x811c9dc5 >>> 0; for (let i = 0; i < d.length; i += 4099) { h = Math.imul(h ^ d[i], 16777619) >>> 0; } return h.toString(16) + ':' + d.length; }

    // ------------------------------------------------------------------ 2. looks: colour -> material
    function neutral(c) { return c.C < 12; }
    function dark(c) { return c.L < 28; }
    function light(c) { return c.L > 80; }
    function lookPop(A) {      // owner memory "what makes a finish pop": contrast between NEIGHBOURS, not saturation
        const K = A.K, out = new Array(K).fill(null), BIG = ['candy', 'matte', 'gloss', 'pearl'], THIN = ['gloss', 'satin_chrome', 'matte'];   // chrome only on thin accents
        A.cl.forEach(function (c) {
            if (c.i === 0) { out[0] = neutral(c) ? (dark(c) ? 'gel' : 'pearl') : 'candy'; return; }
            const fam = (c.share < 0.03 && c.thin > 0.25) ? THIN : BIG;
            let best = null, bv = -1;
            fam.forEach(function (f, rank) {
                let v = 0, w = 0;
                for (let n = 0; n < K; n++) { const a = A.adj[c.i * K + n]; if (!a || !out[n]) continue; v += a * dist(f, out[n]); w += a; }
                if (!w) v = dist(f, out[0]);
                else v /= w;
                v -= rank * 0.5;   // stable tie-break: earlier family wins
                if (v > bv) { bv = v; best = f; }
            });
            out[c.i] = best;
        });
        return out;
    }
    function lookStealth(A) { return A.cl.map(function (c) { return c.i === 0 ? 'matte' : (neutral(c) && dark(c) ? 'gel' : 'gloss'); }); }
    function lookShowroom(A) {
        return A.cl.map(function (c) {
            if (c.i === 0) return neutral(c) ? (dark(c) ? 'gel' : 'pearl') : 'candy';
            if (neutral(c) && light(c)) return 'pearl';
            if (neutral(c) && dark(c)) return 'gel';
            return 'gloss';
        });
    }
    function lookChrome(A) {
        const out = A.cl.map(function (c) { return c.i === 0 ? 'gloss' : (neutral(c) && dark(c) ? 'satin' : 'gloss'); });
        // [SCULPT-2 2026-10-10] accents = non-body colours under 25 % (was 15 %: on ARCA, with the fade read as one colour, the white
        // number outlines + accents are 15.8 % and the look had no chrome at all). Thinnest first: outlines and pinstripes.
        const acc = A.cl.filter(function (c) { return c.i > 0 && c.share < 0.25 && !(neutral(c) && dark(c)); }).sort(function (a, b) { return b.thin - a.thin; });
        if (acc[0]) out[acc[0].i] = 'chrome';
        if (acc[1]) out[acc[1].i] = 'satin_chrome';
        return out;
    }
    function lookSatin(A) {
        return A.cl.map(function (c) {
            if (c.i === 0) return 'satin';
            if (neutral(c) && light(c)) return 'gloss';
            if (neutral(c) && dark(c)) return 'matte';
            return c.C > 25 ? 'metallic' : 'satin';
        });
    }
    const LOOKS = [
        { id: 'pop', name: 'Pop', fn: lookPop, tip: 'Every colour sits next to a different sheen (candy, matte, gloss, pearl; satin chrome on thin lines), so each edge of your design catches the light.' },
        { id: 'stealth', name: 'Stealth', fn: lookStealth, tip: 'Matte body, gloss graphics: the classic wrap trick. Your design shines out of a flat car.' },
        { id: 'showroom', name: 'Showroom', fn: lookShowroom, tip: 'Deep candy body (gel coat or pearl on black, white or grey), gloss graphics, pearl whites.' },
        { id: 'chrome', name: 'Chrome Trim', fn: lookChrome, tip: 'Gloss car; your thinnest accent colour turns to chrome, the next one to satin chrome. Blacks go satin.' },
        { id: 'satin', name: 'Satin Race', fn: lookSatin, tip: 'Modern factory satin: satin body, metallic colour accents, gloss whites, matte blacks.' }
    ];

    // ------------------------------------------------------------------ 3. write / undo the spec layer (exact bytes)
    const U = { undo: [], redo: [] };
    function canApply() {
        const r = RM();
        if (!r || !root.SPBUndoExt || typeof root._recordUndoAction !== 'function') return false;
        return r.ensure();
    }
    function layers(S) {
        if (S.sv) return;
        const n = S.W * S.H;   // the same planes REV-MATERIAL allocates for its first Spec Brush stroke
        S.sv = new Uint8Array(n * 3); S.sc = new Uint8Array(n * 3); S.pv = new Uint8Array(n * 3); S.pc = new Uint8Array(n);
    }
    function tableOf(assign) {
        const M = mats();
        return assign.map(function (id) { const m = id && M[id]; return m ? [m.m, m.r, m.cc] : null; });
    }
    function buildEntry(A, assign) {
        const S = RM().state, N = A.N, lab = A.labels, tb = tableOf(assign);
        const sv = S.sv, sc = S.sc;
        let n = 0;
        for (let i = 0; i < N; i++) { const l = lab[i]; if (l === NB || !tb[l]) continue; const i3 = i * 3; if (sv[i3] | sv[i3 + 1] | sv[i3 + 2] | sc[i3] | sc[i3 + 1] | sc[i3 + 2]) n++; }
        const bIdx = new Int32Array(n), bVal = new Uint8Array(n * 6);
        for (let i = 0, k = 0; i < N && k < n; i++) {
            const l = lab[i]; if (l === NB || !tb[l]) continue; const i3 = i * 3;
            if (sv[i3] | sv[i3 + 1] | sv[i3 + 2] | sc[i3] | sc[i3 + 1] | sc[i3 + 2]) { bIdx[k] = i; bVal.set(sv.subarray(i3, i3 + 3), k * 6); bVal.set(sc.subarray(i3, i3 + 3), k * 6 + 3); k++; }
        }
        let lb = S.lb ? S.lb.slice() : null;
        tb.forEach(function (t, l) { if (!t) return; const b = A.cl[l].box; if (b[2] <= b[0]) return; lb = lb ? [Math.min(lb[0], b[0]), Math.min(lb[1], b[1]), Math.max(lb[2], b[2]), Math.max(lb[3], b[3])] : b.slice(); });
        return { label: 'Spec Sculpt look', labels: lab, tb: tb, assign: assign.slice(), bIdx: bIdx, bVal: bVal, lb0: S.lb ? S.lb.slice() : null, has0: !!S.hasSpec, lb1: lb, sv: sv, N: N };
    }
    function writeEntry(e) {
        const S = RM().state, sv = S.sv, sc = S.sc, lab = e.labels, tb = e.tb, N = e.N;
        for (let i = 0; i < N; i++) {
            const l = lab[i]; if (l === NB) continue; const t = tb[l]; if (!t) continue;
            const i3 = i * 3; sv[i3] = t[0]; sv[i3 + 1] = t[1]; sv[i3 + 2] = t[2]; sc[i3] = 255; sc[i3 + 1] = 255; sc[i3 + 2] = 255;
        }
        if (e.lb1) S.lb = e.lb1.slice();
        S.hasSpec = true;
        settle();
    }
    function eraseEntry(e) {
        const S = RM().state, sv = S.sv, sc = S.sc, lab = e.labels, tb = e.tb, N = e.N;
        for (let i = 0; i < N; i++) {
            const l = lab[i]; if (l === NB || !tb[l]) continue;
            const i3 = i * 3; sv[i3] = sv[i3 + 1] = sv[i3 + 2] = 0; sc[i3] = sc[i3 + 1] = sc[i3 + 2] = 0;
        }
        for (let k = 0; k < e.bIdx.length; k++) { const i3 = e.bIdx[k] * 3; sv.set(e.bVal.subarray(k * 6, k * 6 + 3), i3); sc.set(e.bVal.subarray(k * 6 + 3, k * 6 + 6), i3); }
        S.lb = e.lb0 ? e.lb0.slice() : null;
        S.hasSpec = e.has0;
        settle();
    }
    function settle() {
        const r = RM(); if (!r) return;
        r.state.layerVer++;
        r.changed();     // re-encodes the layer PNGs, emits 'changed', kicks the Live Preview (and the Shine Lens with it)
    }
    function valid(e) { const r = RM(); return !!(r && e && r.state.sv === e.sv && r.state.W * r.state.H === e.N); }
    function undo() { const e = U.undo.pop(); if (!e) return false; if (!valid(e)) { U.undo.length = 0; U.redo.length = 0; return false; } eraseEntry(e); U.redo.push(e); syncUi(); return true; }
    function redo() { const e = U.redo.pop(); if (!e) return false; if (!valid(e)) { U.undo.length = 0; U.redo.length = 0; return false; } writeEntry(e); U.undo.push(e); syncUi(); return true; }
    function registerUndo() {
        if (!root.SPBUndoExt || root.SPBUndoExt.__s2) return !!root.SPBUndoExt;
        root.SPBUndoExt.register(KIND, {
            hasUndo: function () { return U.undo.length > 0; }, hasRedo: function () { return U.redo.length > 0; },
            undo: undo, redo: redo, clearRedo: function () { U.redo.length = 0; },
            label: function () { return 'Spec Sculpt look'; }
        });
        root.SPBUndoExt.__s2 = 1;
        try { RM() && RM().on(function (what) { if (what === 'reset') { U.undo.length = 0; U.redo.length = 0; } }); } catch (_) {}
        return true;
    }
    /** Apply a colour -> material assignment. While the panel session's own step is still the newest one it is replaced in place
     *  (one Ctrl+Z step however many looks were tried), otherwise a new step is recorded. Returns ms. */
    function apply(assign) {
        if (off() || !P.A) return -1;
        if (!canApply() || !registerUndo()) { toast('Spec Sculpt needs the Material tools (REV-MATERIAL) on: nothing was changed.', 'warning'); return -1; }
        const t0 = performance.now(), S = RM().state;
        if (S.W * S.H !== P.A.N) { toast('The paint changed size: Spec Sculpt read the car again.', 'info'); return -1; }
        layers(S);
        const top = U.undo[U.undo.length - 1];
        if (P.entry && top === P.entry && !U.redo.length && valid(P.entry)) {
            eraseEntry(P.entry);
            const e = buildEntry(P.A, assign);
            Object.keys(e).forEach(function (k) { P.entry[k] = e[k]; });
            writeEntry(P.entry);
        } else {
            const e = buildEntry(P.A, assign);
            writeEntry(e);
            U.undo.push(e); U.redo.length = 0;
            if (U.undo.length > 12) U.undo.shift();
            try { if (typeof root._clearAllRedos === 'function') root._clearAllRedos(); } catch (_) {}
            try { root._recordUndoAction(KIND); } catch (_) {}
            P.entry = e;
        }
        P.ms = Math.round(performance.now() - t0);
        return P.ms;
    }

    // ------------------------------------------------------------------ 4. panel
    const ICON = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="5.6"/><path d="M4.6 6.2a4 4 0 0 1 3.4-2"/><circle cx="5.6" cy="5.6" r="1" fill="currentColor" stroke="none"/></svg>';
    const XI = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>';
    const P = { el: null, A: null, look: null, assign: null, entry: null, lensWas: null, ms: 0, busy: false };

    function lens() { const L = root.SPBRevLens; return L && !L.off && typeof L.setMode === 'function' ? L : null; }
    function shineBarShown() { const b = doc.getElementById('spbShineBar'); return !!(b && b.offsetParent); }
    function rect(sel) { const e = doc.querySelector(sel); if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return r.width > 20 && r.height > 20 ? r : null; }
    function dockPos(el) {   // the same dock rule as the POLISH-H shell: a free gutter beside the canvases, never over the Live Preview
        const vw = root.innerWidth, vh = root.innerHeight, w = el.offsetWidth || 352;
        const bar = rect('#spbTopToolbar'); let top = Math.round(bar ? bar.bottom + 6 : 120);
        const src = rect('#splitSource'), prv = rect('#splitPreview'), cen = rect('#centerPanel');
        let L = Math.min(src ? src.left : 1e9, prv ? prv.left : 1e9), R = Math.max(src ? src.right : -1e9, prv ? prv.right : -1e9);
        if (L > 1e8) { L = cen ? cen.left : 0; R = cen ? cen.right : vw; }
        let x;
        if (L - 16 >= w) x = L - w - 10; else if (vw - R - 16 >= w) x = R + 10; else x = 6;
        x = Math.max(4, Math.min(vw - w - 4, Math.round(x)));
        // [LEFTOVERS-3 item 1, 2026-10-10] at 1100 px there is no gutter, so the dock (x = 6, just under the tool band) landed over the RENDER
        // button (213..363 x 123..159 at 1100x800): until the painter dragged the panel away RENDER could not be clicked. When the panel's
        // column would cover the RENDER button, start the panel just below it instead (the body scrolls, header and footer stay).
        // Before: panel 6..342 x 125..792, 4386 px^2 over RENDER, RENDER's centre hit-tests to the panel. After: see leftovers3/PROGRESS.md.
        if (!lo3off(1)) {
            const rb = rect('#btnRender');
            if (rb && x < rb.right + 6 && x + w > rb.left - 6 && top < rb.bottom + 6) top = Math.round(rb.bottom + 8);
        }
        top = Math.max(4, Math.min(vh - 160, top));
        return { x: x, y: top, mh: Math.max(220, vh - top - 8) };
    }
    function piOff() { return !!(root.SPB_POLISH_I_OFF || root.SPB_POLISH_I_1_OFF); }
    function place() {
        const el = P.el; if (!el || el.__moved) return;
        /* [POLISH-I 2026-10-10 item 1] one dock rule for every panel: the POLISH-H shell's dockPos now keeps RENDER, the colour row under it, the tool
           options bar and the Live Preview clear (it also caps the height above the options bar). This panel used its own copy (LEFTOVERS-3 only fixed
           RENDER: at 1100x800 the panel 6..342 x 167..792 still covered the left part of the options bar, 3999 px^2). Fallback = the local rule below
           (no shell, shell off, or SPB_POLISH_I_OFF). */
        const PH = root.__spbPolishH;
        if (!piOff() && PH && typeof PH.applyDock === 'function' && !(typeof PH.isOff === 'function' && PH.isOff())) {
            if (PH.applyDock(el)) { if (!P.hooked && typeof PH.onLayout === 'function') { P.hooked = true; PH.onLayout(function () { if (P.el && P.el.isConnected && !P.el.hidden && P.el.style.display !== 'none' && !P.el.__moved && !piOff()) place(); }); } return; }
        }
        const p = dockPos(el);
        el.style.left = p.x + 'px'; el.style.top = p.y + 'px'; el.style.maxHeight = p.mh + 'px';
        if (!lo3off(1)) el.style.setProperty('--ph-top', p.y + 'px'); else el.style.removeProperty('--ph-top');   // [LEFTOVERS-3 item 1] the POLISH-H shell caps max-height at 100vh - var(--ph-top, 125px) !important: tell it where the dock really starts
    }
    function ensurePanel() {
        if (P.el && P.el.isConnected) return P.el;
        const p = doc.createElement('div');
        p.id = 'spbSculpt2Panel'; p.className = 'spb-ph-panel spb-s2'; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', 'Spec Sculpt');
        p.innerHTML =
            '<div class="spb-ph-head spb-s2-head"><span class="spb-s2-ico">' + ICON + '</span><span class="spb-ph-ttl">Spec Sculpt</span>' +
            '<button type="button" class="spb-ph-x" data-s2="cancel" aria-label="Close Spec Sculpt" title="Close and step this look back (Esc)">' + XI + '</button></div>' +
            '<div class="spb-s2-body">' +
            '<p class="spb-s2-lead">Give the whole car a spec look from your paint\'s colours. Spec only: your paint is not touched.</p>' +
            '<div class="spb-s2-sec">Looks</div><div class="spb-s2-looks" role="group" aria-label="Spec looks"></div>' +
            '<div class="spb-s2-tip" aria-live="polite"></div>' +
            '<div class="spb-s2-sec">Your Colours <span class="spb-s2-n"></span></div><div class="spb-s2-cols"></div>' +
            // [SHINE-OFF 2026-10-12 owner: no artificial shine; "REMOVE the SHINE LENS"] the Light row drove the removed Shine Lens and
            // printed "The Shine Lens is off in this build". Hidden (DOM kept: the code below still queries it). Do not re-show.
            '<div class="spb-s2-lightwrap" style="display:none" aria-hidden="true"><div class="spb-s2-sec">Light</div>' +
            '<div class="spb-s2-light"><canvas class="spb-s2-puck" width="56" height="56" role="slider" tabindex="0" aria-label="Studio light direction" title="Drag to move the studio light. Arrow keys nudge it."></canvas>' +
            '<div class="spb-s2-lbtns"><button type="button" data-s2="full" title="The whole Live Preview under a studio light">Studio</button><button type="button" data-s2="sweep" title="The light circles the car so candy, chrome and pearl flash">Sweep</button><button type="button" data-s2="lensoff" title="Back to the flat Live Preview">Off</button></div>' +
            '<div class="spb-s2-lhint"></div></div></div>' +
            '<div class="spb-s2-sec">Spec Mix</div><div class="spb-s2-mix" aria-live="polite"></div>' +
            '<div class="spb-s2-status" aria-live="polite"></div>' +
            '</div>' +
            '<div class="spb-ph-foot spb-s2-foot"><button type="button" class="spb-s2-lab" data-s2="lab" title="Open the classic Spec Sculpt lab (its own window): spec TGAs from a file, batch folders, photo matching">Classic Lab</button>' +
            '<span class="spb-s2-sp"></span><button type="button" data-s2="cancel" title="Step this look back and close">Cancel</button><button type="button" class="spb-ph-primary" data-s2="keep" title="Keep this look (Ctrl+Z steps it back)">Keep Look</button></div>';
        doc.body.appendChild(p);
        P.el = p;
        p.addEventListener('click', onClick);
        p.addEventListener('change', onChange);
        p.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); e.preventDefault(); cancel(); } });
        wireDrag(p);
        wirePuck(p.querySelector('.spb-s2-puck'));
        return p;
    }
    function wireDrag(p) {
        const head = p.querySelector('.spb-s2-head');
        head.addEventListener('pointerdown', function (e) {
            if (e.button !== 0 || e.target.closest('button')) return;
            const r = p.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
            function mv(ev) { p.__moved = true; p.style.left = Math.max(0, Math.min(root.innerWidth - 80, ev.clientX - dx)) + 'px'; p.style.top = Math.max(0, Math.min(root.innerHeight - 40, ev.clientY - dy)) + 'px'; }
            function up() { doc.removeEventListener('pointermove', mv); doc.removeEventListener('pointerup', up); }
            doc.addEventListener('pointermove', mv); doc.addEventListener('pointerup', up);
        });
        head.addEventListener('dblclick', function () { p.__moved = false; place(); });
    }
    function drawPuck(cv) {
        if (!cv) return;
        const x = cv.getContext('2d'), n = cv.width, L = lens(), g = L && L.getLight ? L.getLight() : { az: -0.9, el: 0.78 };
        x.clearRect(0, 0, n, n);
        const r = n / 2 - 3, cx = n / 2, cy = n / 2, k = Math.cos(g.el);
        const lx = cx + Math.cos(g.az) * r * k, ly = cy - Math.sin(g.az) * r * k;
        const gr = x.createRadialGradient(lx, ly, 1, cx, cy, r);
        gr.addColorStop(0, '#f4f7ff'); gr.addColorStop(0.35, '#7d8796'); gr.addColorStop(1, '#1b1d22');
        x.fillStyle = gr; x.beginPath(); x.arc(cx, cy, r, 0, Math.PI * 2); x.fill();
        x.strokeStyle = 'rgba(63,186,181,.8)'; x.lineWidth = 1.5; x.beginPath(); x.arc(cx, cy, r, 0, Math.PI * 2); x.stroke();
        x.fillStyle = '#ffd23a'; x.beginPath(); x.arc(lx, ly, 3.5, 0, Math.PI * 2); x.fill();
    }
    function setLightFrom(cv, ev) {
        const L = lens(); if (!L || !L.setLight) return;
        const r = cv.getBoundingClientRect(), n = r.width / 2 - 3, dx = (ev.clientX - r.left - r.width / 2) / n, dy = -(ev.clientY - r.top - r.height / 2) / n;
        const d = Math.min(1, Math.sqrt(dx * dx + dy * dy));
        L.setLight(Math.atan2(dy, dx), Math.acos(Math.max(0.07, d)));
        if (L.getMode && L.getMode() === 'off' && shineBarShown()) L.setMode('full');
        if (L.getMode && L.getMode() === 'sweep') L.setMode('full');
        drawPuck(cv);
    }
    function wirePuck(cv) {
        cv.addEventListener('pointerdown', function (e) {
            if (e.button !== 0) return;
            e.preventDefault(); try { cv.setPointerCapture(e.pointerId); } catch (_) {}
            setLightFrom(cv, e);
            function mv(ev) { setLightFrom(cv, ev); }
            function up() { cv.removeEventListener('pointermove', mv); cv.removeEventListener('pointerup', up); }
            cv.addEventListener('pointermove', mv); cv.addEventListener('pointerup', up);
        });
        cv.addEventListener('keydown', function (e) {
            const L = lens(); if (!L || !L.setLight) return;
            const k = { ArrowLeft: [0.12, 0], ArrowRight: [-0.12, 0], ArrowUp: [0, 0.08], ArrowDown: [0, -0.08] }[e.key];
            if (!k) return; e.preventDefault(); const g = L.getLight(); L.setLight(g.az + k[0], g.el + k[1]); drawPuck(cv);
        });
    }
    function renderLooks() {
        const box = P.el.querySelector('.spb-s2-looks');
        box.innerHTML = LOOKS.map(function (l) {
            return '<button type="button" class="spb-s2-look' + (P.look === l.id ? ' on' : '') + '" data-look="' + l.id + '" aria-pressed="' + (P.look === l.id) + '" title="' + esc(l.tip) + '">' + esc(l.name) + '</button>';
        }).join('');
        const lk = LOOKS.find(function (l) { return l.id === P.look; });
        P.el.querySelector('.spb-s2-tip').textContent = lk ? lk.tip : 'Pick a look. You can change any colour\'s material below.';
    }
    function renderCols() {
        const A = P.A, M = mats(), box = P.el.querySelector('.spb-s2-cols');
        P.el.querySelector('.spb-s2-n').textContent = A ? '(' + A.K + ')' : '';
        if (!A) { box.innerHTML = '<div class="spb-s2-empty">Load a paint first.</div>'; return; }
        const opts = function (sel) {
            return '<option value=""' + (!sel ? ' selected' : '') + '>Leave (zones decide)</option>' + ORDER.map(function (id) {
                return '<option value="' + id + '"' + (sel === id ? ' selected' : '') + '>' + esc(M[id].name) + '</option>';
            }).join('');
        };
        box.innerHTML = A.cl.map(function (c) {
            const sel = P.assign ? P.assign[c.i] : null;
            // a blend (smooth fade of several colours) shows its fade as the swatch and is one row, one material
            const bg = c.blend ? 'linear-gradient(90deg,' + c.blend.join(',') + ')' : c.hex;
            const tip = c.blend ? 'Fade: ' + c.blend.join(' > ') + ' (one material, no seam across the fade)' : c.hex;
            return '<div class="spb-s2-col"><span class="spb-s2-sw" style="background:' + bg + '" title="' + esc(tip) + '"></span>' +
                '<span class="spb-s2-pc">' + (c.share * 100 < 1 ? (c.share * 100).toFixed(1) : Math.round(c.share * 100)) + '%' + (c.i === 0 ? ' body' : (c.blend ? ' fade' : '')) + '</span>' +
                '<select data-col="' + c.i + '" aria-label="Material for ' + (c.blend ? 'the colour fade' : 'colour ' + c.hex) + '">' + opts(sel) + '</select></div>';
        }).join('');
    }
    function renderMix() {
        const A = P.A, box = P.el.querySelector('.spb-s2-mix');
        if (!A || !P.assign) { box.innerHTML = '<div class="spb-s2-empty">No look yet: the zones decide the spec.</div>'; return; }
        const fam = { chrome: 0, metal: 0, gloss: 0, satin: 0, matte: 0, zones: 0 };
        A.cl.forEach(function (c) { const id = P.assign[c.i]; fam[id ? FAMILY[id] : 'zones'] += c.share; });
        const col = { chrome: '#d9e2ea', metal: '#c9a03f', gloss: '#3fbab5', satin: '#7f8aa0', matte: '#3a3d45', zones: 'repeating-linear-gradient(45deg,#2a2b30 0 4px,#34363c 4px 8px)' };
        const nm = { chrome: 'Chrome', metal: 'Metal', gloss: 'Gloss', satin: 'Satin', matte: 'Matte', zones: 'Zones' };
        const keys = Object.keys(fam).filter(function (k) { return fam[k] > 0.0005; });
        box.innerHTML = '<div class="spb-s2-bar">' + keys.map(function (k) { return '<span style="flex:' + fam[k].toFixed(4) + ';background:' + col[k] + '" title="' + nm[k] + ' ' + Math.round(fam[k] * 100) + '%"></span>'; }).join('') + '</div>' +
            '<div class="spb-s2-leg">' + keys.map(function (k) { return '<span><i style="background:' + col[k] + '"></i>' + nm[k] + ' ' + (fam[k] * 100 < 1 ? '<1' : Math.round(fam[k] * 100)) + '%</span>'; }).join('') + '</div>';
    }
    function renderLight() {
        const L = lens(), h = P.el.querySelector('.spb-s2-lhint'), mode = L && L.getMode ? L.getMode() : 'off';
        P.el.querySelectorAll('.spb-s2-lbtns button').forEach(function (b) { const m = b.getAttribute('data-s2'); b.classList.toggle('on', (m === 'lensoff' ? 'off' : m) === mode); b.disabled = !L || !shineBarShown(); });
        h.textContent = !L ? 'The Shine Lens is off in this build.' : (!shineBarShown() ? 'Switch the view to Split or Preview to see the look under the light.' : 'Drag the light. Chrome flashes, satin glows, matte stays flat.');
        drawPuck(P.el.querySelector('.spb-s2-puck'));
    }
    function status(t) { if (P.el) P.el.querySelector('.spb-s2-status').textContent = t || ''; }
    function syncUi() {
        if (!P.el || !P.el.isConnected || P.el.hidden) return;
        // a Ctrl+Z / Ctrl+Y of this session's step while the panel is open: show what is really on the car
        if (P.entry && U.undo.indexOf(P.entry) < 0) { P.look = null; P.assign = null; P.entry = null; renderLooks(); renderCols(); renderMix(); status('Look stepped back.'); }
    }
    function onClick(e) {
        const b = e.target.closest('button'); if (!b || !P.el.contains(b)) return;
        const lk = b.getAttribute('data-look');
        if (lk) { pickLook(lk); return; }
        const a = b.getAttribute('data-s2');
        if (a === 'keep') keep();
        else if (a === 'cancel') cancel();
        else if (a === 'lab') openLab();
        else if (a === 'full' || a === 'sweep' || a === 'lensoff') { const L = lens(); if (L) L.setMode(a === 'lensoff' ? 'off' : a); renderLight(); }
    }
    function onChange(e) {
        const s = e.target.closest('select[data-col]'); if (!s || !P.A) return;
        const assign = P.assign ? P.assign.slice() : new Array(P.A.K).fill(null);
        assign[+s.getAttribute('data-col')] = s.value || null;
        P.look = null; P.assign = assign;
        run();
    }
    function pickLook(id) {
        const l = LOOKS.find(function (x) { return x.id === id; }); if (!l || !P.A) return;
        P.look = id; P.assign = l.fn(P.A);
        run();
    }
    function run() {
        const ms = apply(P.assign);
        renderLooks(); renderCols(); renderMix();
        if (ms >= 0) status('Applied in ' + ms + ' ms. The Live Preview updates in a moment; RENDER writes exactly these values.');
    }
    /* [TICKETS-4 2026-10-10 item 3] UI-B: at 1100x800 the panel (no gutter beside the canvases, docked at the left edge) sat over SOURCE and hid its left 40%; its Light
       row was cut by the footer. The Light block is now pinned to the bottom of the body (css .spb-s2-lightwrap, sticky) so the footer can never cut it. And when the
       docked panel would cover SOURCE the stage shows the Live Preview only (a temporary view, __spbPolishG.setMode('preview', false)): Sculpt only edits what the Live
       Preview shows, the Preview then sits right of the panel, and closing the panel hands the view back. Kill switch window.SPB_T4_OFF / SPB_T4_3_OFF. */
    function t4off3() { return !!(root.SPB_T4_OFF || root.SPB_T4_3_OFF); }
    function t4Preview() {
        try { doc.body.classList.toggle('spb-t4-3-off', t4off3()); } catch (_) {}
        if (t4off3() || !P.el) return;
        const PG = root.__spbPolishG, src = rect('#splitSource'); if (!PG || !PG.state || !src) return;
        const pr = P.el.getBoundingClientRect();
        if (pr.right > src.left + 4 && pr.left < src.right - 4 && pr.bottom > src.top + 4 && pr.top < src.bottom - 4) {
            const e = PG.state().eff;
            if (e === 'split' || e === 'source') { PG.setMode('preview', false); P.t4view = true; }
        }
    }
    function t4Restore() { if (P.t4view) { P.t4view = false; try { const PG = root.__spbPolishG; if (PG && PG.clearTmp) PG.clearTmp(); } catch (_) {} } }
    async function open() {
        if (off()) return openLab();
        const p = ensurePanel();
        p.hidden = false; p.style.display = '';
        place();
        t4Preview();
        P.look = null; P.assign = null; P.entry = null;
        renderLooks(); renderCols(); renderMix(); renderLight();
        status('Reading your paint...');
        const L = lens();
        P.lensWas = L && L.getMode ? L.getMode() : null;
        if (L && P.lensWas === 'off' && shineBarShown()) { try { L.setMode('full'); } catch (_) {} }
        renderLight();
        try {
            P.A = await analyse();
        } catch (err) { P.A = null; console.warn('[SPB-SCULPT2] analyse', err); }
        renderCols(); renderMix();
        if (!P.A) { status('No paint to read yet: load a paint (or PSD) first.'); return; }
        status('Read ' + P.A.K + ' colours in ' + P.A.ms + ' ms' + (P.A.bodyMask ? ' (body only).' : '.') + ' Pick a look.');
        const first = p.querySelector('.spb-s2-look'); if (first) try { first.focus({ preventScroll: true }); } catch (_) {}
    }
    function closePanel() {
        if (!P.el) return;
        P.el.hidden = true; P.el.style.display = 'none';
        t4Restore();
        const L = lens();
        if (L && P.lensWas === 'off') { try { L.setMode('off'); } catch (_) {} }
        P.lensWas = null;
    }
    function keep() {
        const had = !!P.entry;
        P.entry = null; P.look = null; P.assign = null;
        closePanel();
        if (had) toast('Spec Sculpt look kept. Ctrl+Z steps it back; RENDER and Save include it.', 'success');
    }
    function cancel() {
        const e = P.entry;
        let trailTop = null;
        try { /* global lexical in paint-booth-3-canvas.js, not a window property */ const tr = (typeof _undoActionTrail !== 'undefined') ? _undoActionTrail : root._undoActionTrail; trailTop = Array.isArray(tr) && tr.length ? tr[tr.length - 1] : null; } catch (_) {}
        if (e && U.undo[U.undo.length - 1] === e && trailTop === KIND && typeof root.undoDrawStroke === 'function') {
            // nothing else was done since: the app's own Ctrl+Z steps it back, so the app's undo trail stays honest
            try { root.undoDrawStroke(); } catch (_) {}
        } else if (e && U.undo.indexOf(e) >= 0) {
            toast('You changed other things after this look: use Ctrl+Z to step it back.', 'info');
        }
        P.entry = null; P.look = null; P.assign = null;
        closePanel();
    }
    function openLab() {
        const N = root.SpbNuq, o = N && N.openSpecSculpt && N.openSpecSculpt.__s2orig;
        if (P.el && !P.el.hidden) keep();
        if (typeof root.openSpecSculptLab === 'function') root.openSpecSculptLab();
        else if (o) o();
        else root.open('/spec-sculpt.html', 'shokkerSpecSculptLab');   // never navigate the editor away (no dead ends)
    }

    // ------------------------------------------------------------------ 5. entry points: SPEC SCULPT header button + Material / Spec menu
    function hookHeader() {
        const N = root.SpbNuq;
        if (N && typeof N.openSpecSculpt === 'function' && !N.openSpecSculpt.__s2) {
            const orig = N.openSpecSculpt;
            const w = function (btn) { if (off()) return orig.apply(this, arguments); open(); };
            w.__s2 = 1; w.__s2orig = orig;
            N.openSpecSculpt = w;
        }
        const hb = doc.querySelector('[data-testid="btn-spec-sculpt"]');
        if (hb) {
            if (!hb.__s2t) hb.__s2t = hb.getAttribute('title') || '';
            const want = off() ? hb.__s2t : 'Spec Sculpt: give the whole car a spec look from your paint colours (Pop, Stealth, Showroom...) and see it live under the studio light. The classic lab is one click away inside.';
            if (hb.getAttribute('title') !== want) hb.setAttribute('title', want);
            if (!N && !hb.__s2c) {   // no NUQ router in this build: take the click ourselves (capture), kill switch falls through
                hb.__s2c = 1;
                hb.addEventListener('click', function (e) { if (off()) return; e.stopImmediatePropagation(); e.preventDefault(); open(); }, true);
            }
        }
    }
    function menuButton() {
        const b = doc.createElement('button');
        b.type = 'button'; b.className = 'vtool-btn spb-s2-menu'; b.setAttribute('data-spb-sculpt2', '1');
        b.title = 'Spec Sculpt: one-click spec looks for the whole car from your paint colours, live under the studio light';
        b.innerHTML = '<span class="spb-mi-ico">' + ICON + '</span> Spec Sculpt…';
        b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); const d = b.closest('details'); if (d) d.removeAttribute('open'); open(); });
        return b;
    }
    function inject() {
        const pop = doc.querySelector('#spbRevMatMenu .spb-tb-pop');
        let me = doc.querySelector('[data-spb-sculpt2]');
        if (off()) { if (me) me.remove(); return; }
        if (!pop) return;
        if (!me) me = menuButton();
        if (me.parentNode !== pop) pop.appendChild(me);
    }
    function init() {
        let n = 0;
        const t = setInterval(function () { try { hookHeader(); inject(); } catch (e) { console.warn('[SPB-SCULPT2] init', e); } if (++n > 90) clearInterval(t); }, 1000);
        try { hookHeader(); inject(); registerUndo(); } catch (e) { console.warn('[SPB-SCULPT2] init', e); }
        root.addEventListener('resize', function () { if (P.el && !P.el.hidden) place(); });
        // keep the light buttons honest when the view changes (Split / Source / Preview)
        setInterval(function () { if (P.el && !P.el.hidden && P.el.isConnected) renderLight(); }, 1500);
    }

    root.SPBSculpt2 = {
        version: VERSION, off: off, open: open, keep: keep, cancel: cancel, openLab: openLab,
        analyse: analyse, looks: LOOKS, mats: mats, apply: apply, pickLook: pickLook, state: P, undoState: U,
        setColour: function (i, id) { if (!P.A) return -1; const a = P.assign ? P.assign.slice() : new Array(P.A.K).fill(null); a[i] = id || null; P.look = null; P.assign = a; run(); return P.ms; }
    };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
