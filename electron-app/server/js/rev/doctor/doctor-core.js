/* [SPB-REV-DOCTOR 2026-10-10] Spec Doctor core: pure analysis of the car's paint + spec (what RENDER writes)
 * against the mistakes that make iRacing paints look wrong in the sim, plus the pixel maths of each fix.
 * No DOM. Runs in the page (window.SPBDoctorCore) and in Node for calibration (module.exports).
 * iRacing spec semantics: R = metallic, G = roughness (0 = mirror), B = clearcoat (0-15 none, 16 = max gloss .. 255 dull),
 * A = spec mask. Every threshold below is calibrated - see _easy_claude_work/rev_tools/doctor/DESIGN.md. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBDoctorCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';
    const VERSION = 'rev-doctor-2026-10-10e';

    // ------------------------------------------------------------------ thresholds (calibrated; DESIGN.md "Thresholds")
    const T = {
        minArea: 400,                 // px at 2048: smaller spots are invisible at sim distance (a 20x20 px patch)
        c1: { metalM: 200, roughG: 60, darkV: 40, open: 2, maskA: 128, flatSd: 4, blackV: 12, bigArea: 20000, bigFill: 0.6 },
        c2: { glossG: 40, dullB: 128, zeroFrac: 0.95, flatStd: 12, pxMaxM: 100, pxDullB: 240 },
        c3: { metalM: 160, roughG: 80, metalFrac: 0.6, inheritD: 24, ring: 12, gap: 3, minPx: 300 },
        c4: { flatStd: 2.0, artStd: 18, minBody: 0.05 },
        c5: { edge: 48, tile: 64, maxShift: 8, minEdges: 48, aligned: 0.45, best: 0.6, gain: 0.3, minShift: 2, minTiles: 3, chain: 3, haloD: 24 },
        c6: { tile: 32, rms: 14, dens: 0.35, devPx: 10, minTiles: 3, minBody: 0.5, struct: 0.3, quietM: 7, authFrac: 0.5 }
    };

    // ------------------------------------------------------------------ primitives
    function boxMean(src, W, H, r) {          // separable box mean, clamped edges -> Float32Array
        const tmp = new Float32Array(W * H), out = new Float32Array(W * H), d = 2 * r + 1;
        for (let y = 0; y < H; y++) {
            const row = y * W; let s = 0;
            for (let k = -r; k <= r; k++) s += src[row + Math.min(W - 1, Math.max(0, k))];
            for (let x = 0; x < W; x++) {
                tmp[row + x] = s / d;
                s += src[row + Math.min(W - 1, x + r + 1)] - src[row + Math.max(0, x - r)];
            }
        }
        for (let x = 0; x < W; x++) {
            let s = 0;
            for (let k = -r; k <= r; k++) s += tmp[Math.min(H - 1, Math.max(0, k)) * W + x];
            for (let y = 0; y < H; y++) {
                out[y * W + x] = s / d;
                s += tmp[Math.min(H - 1, y + r + 1) * W + x] - tmp[Math.max(0, y - r) * W + x];
            }
        }
        return out;
    }
    function dilate(m, W, H, r) {             // binary square dilation (0/1 Uint8Array)
        if (r <= 0) return m.slice();
        const hz = new Uint8Array(W * H), out = new Uint8Array(W * H);
        for (let y = 0; y < H; y++) {
            const row = y * W; let last = -1e9;
            for (let x = 0; x < W; x++) { if (m[row + x]) last = x; if (x - last <= r) hz[row + x] = 1; }
            last = 1e9;
            for (let x = W - 1; x >= 0; x--) { if (m[row + x]) last = x; if (last - x <= r) hz[row + x] = 1; }
        }
        for (let x = 0; x < W; x++) {
            let last = -1e9;
            for (let y = 0; y < H; y++) { if (hz[y * W + x]) last = y; if (y - last <= r) out[y * W + x] = 1; }
            last = 1e9;
            for (let y = H - 1; y >= 0; y--) { if (hz[y * W + x]) last = y; if (last - y <= r) out[y * W + x] = 1; }
        }
        return out;
    }
    function invert(m) { const o = new Uint8Array(m.length); for (let i = 0; i < m.length; i++) o[i] = m[i] ? 0 : 1; return o; }
    function erode(m, W, H, r) { return invert(dilate(invert(m), W, H, r)); }
    function open(m, W, H, r) { return dilate(erode(m, W, H, r), W, H, r); }
    function components(m, W, H, minArea) {   // 4-connected; returns {lab, comps:[{id,area,bbox,cx,cy}]}
        const lab = new Int32Array(W * H), comps = [], st = new Int32Array(W * H);
        let id = 0;
        for (let i = 0; i < W * H; i++) {
            if (!m[i] || lab[i]) continue;
            id++; let sp = 0, area = 0, x0 = W, y0 = H, x1 = -1, y1 = -1, sx = 0, sy = 0;
            st[sp++] = i; lab[i] = id;
            while (sp) {
                const p = st[--sp], x = p % W, y = (p / W) | 0;
                area++; sx += x; sy += y;
                if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
                if (x > 0 && m[p - 1] && !lab[p - 1]) { lab[p - 1] = id; st[sp++] = p - 1; }
                if (x < W - 1 && m[p + 1] && !lab[p + 1]) { lab[p + 1] = id; st[sp++] = p + 1; }
                if (y > 0 && m[p - W] && !lab[p - W]) { lab[p - W] = id; st[sp++] = p - W; }
                if (y < H - 1 && m[p + W] && !lab[p + W]) { lab[p + W] = id; st[sp++] = p + W; }
            }
            comps.push({ id: id, area: area, bbox: [x0, y0, x1 + 1, y1 + 1], cx: Math.round(sx / area), cy: Math.round(sy / area) });
        }
        return { lab: lab, comps: comps.filter(function (c) { return c.area >= (minArea || 0); }) };
    }
    function keepComps(lab, comps, n) {       // mask of the kept components only
        const keep = new Uint8Array(comps.length ? comps[comps.length - 1].id + 1 : 1), out = new Uint8Array(n);
        let any = false;
        comps.forEach(function (c) { if (c.id >= keep.length) return; keep[c.id] = 1; any = true; });
        if (!any) return out;
        for (let i = 0; i < n; i++) if (lab[i] && lab[i] < keep.length && keep[lab[i]]) out[i] = 1;
        return out;
    }
    function bodyOf(body, n) { if (body && body.length === n) { const b = new Uint8Array(n); for (let i = 0; i < n; i++) b[i] = body[i] ? 1 : 0; return b; } const b = new Uint8Array(n); b.fill(1); return b; }
    function count(m) { let c = 0; for (let i = 0; i < m.length; i++) if (m[i]) c++; return c; }
    function bboxOf(m, W, H) {
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        for (let y = 0; y < H; y++) { const r = y * W; for (let x = 0; x < W; x++) if (m[r + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
        return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
    }
    function median(arr) { if (!arr.length) return 0; const a = Float32Array.from(arr).sort(); return a[a.length >> 1]; }
    function regionsOf(m, W, H, minArea) {
        const cc = components(m, W, H, minArea);
        return cc.comps.sort(function (a, b) { return b.area - a.area; }).slice(0, 24).map(function (c) { return { bbox: c.bbox, area: c.area, cx: c.cx, cy: c.cy }; });
    }
    function toHeat(m) { const h = new Uint8Array(m.length); for (let i = 0; i < m.length; i++) if (m[i]) h[i] = 255; return h; }

    // ------------------------------------------------------------------ C1: chrome / mirror metal over near-black paint
    function checkChromeDark(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, P = ctx.paint, S = ctx.spec, B = ctx.body, t = T.c1;
        const v = new Uint8Array(n);                       // brightest channel = the metal's reflectance in its best channel
        for (let i = 0, j = 0; i < n; i++, j += 4) { const r = P[j], g = P[j + 1], b = P[j + 2]; v[i] = r > g ? (r > b ? r : b) : (g > b ? g : b); }
        const vm = boxMean(v, W, H, 2);
        let m = new Uint8Array(n);
        for (let i = 0, j = 0; i < n; i++, j += 4) if (B[i] && S[j] >= t.metalM && S[j + 1] <= t.roughG && S[j + 3] >= t.maskA && vm[i] <= t.darkV) m[i] = 1;
        m = open(m, W, H, t.open);
        const cc = components(m, W, H, T.minArea);
        if (!cc.comps.length) return null;
        // intent guard (calibrated 2026-10-10): a painter's mistake is chrome over a FLAT dark fill (a black stripe, number,
        // base). Designed dark-mirror looks (PROTECTED Hologram Metal: cells V 21-27, sd 6.9-8.8) are textured. Keep a
        // component when its eroded interior is flat (sd <= flatSd) or truly black (mean <= blackV), or when it is a big
        // solid patch (area >= bigArea and bbox fill >= bigFill): Hologram Metal's dark cells are a lace of small cells
        // (largest 8,090 px, fill 0.38-0.54) while chrome over a textured black livery panel is one solid region (owner
        // car planted 2026-10-10: 89,880 px, fill 0.87, interior sd 11.4 - the flat test alone missed it).
        const core = erode(keepComps(cc.lab, cc.comps, n), W, H, 2);
        const L = cc.comps[cc.comps.length - 1].id + 1, s1 = new Float64Array(L), s2 = new Float64Array(L), kk = new Float64Array(L);
        for (let i = 0; i < n; i++) { if (!core[i]) continue; const l = cc.lab[i]; s1[l] += v[i]; s2[l] += v[i] * v[i]; kk[l]++; }
        cc.comps = cc.comps.filter(function (c) {
            const k = kk[c.id]; if (!k) return true;            // too thin to erode: a stroke, judge by colour alone
            const mu = s1[c.id] / k, sd = Math.sqrt(Math.max(0, s2[c.id] / k - mu * mu));
            const fill = c.area / Math.max(1, (c.bbox[2] - c.bbox[0]) * (c.bbox[3] - c.bbox[1]));
            return sd <= t.flatSd || mu <= t.blackV || (c.area >= t.bigArea && fill >= t.bigFill);
        });
        if (!cc.comps.length) return null;
        const heat = keepComps(cc.lab, cc.comps, n);
        let sv = 0, sm = 0, sg = 0, sb = 0, k = 0;
        for (let i = 0, j = 0; i < n; i++, j += 4) if (heat[i]) { sv += vm[i]; sm += S[j]; sg += S[j + 1]; sb += S[j + 2]; k++; }
        const area = k, meanV = sv / k, meanB = sb / k, bare = meanB <= 15;
        return {
            // severity by clearcoat: with no coat (B 0-15) nothing but the black metal reflects -> a black hole; with a
            // coat the clearcoat still throws highlights, so the chrome is merely wasted (reads as gloss black)
            check: 'chrome-dark', severity: bare ? 'high' : 'medium', title: 'Chrome Over Near-Black Paint',
            why: bare
                ? 'In iRacing metal reflects in the paint colour, so chrome on near-black paint with no clearcoat reflects almost nothing and shows up as a black hole on track.'
                : 'In iRacing metal reflects in the paint colour, so this chrome on near-black paint is invisible: only the clearcoat shines and it reads as plain gloss black.',
            area: area, heat: toHeat(heat), regions: regionsOf(heat, W, H, T.minArea),
            stats: { meanBrightest: Math.round(meanV), meanM: Math.round(sm / k), meanG: Math.round(sg / k), meanB: Math.round(meanB) },
            fixes: [{ id: 'lift-bright', label: 'Lighten Paint For Bright Chrome' }, { id: 'dark-chrome', label: 'Make It A Proper Dark Chrome' }]
        };
    }

    // ------------------------------------------------------------------ C2: clearcoat confusion
    function checkClearcoat(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, S = ctx.spec, B = ctx.body, t = T.c2, out = [], A = ctx.authored;
        let none = new Uint8Array(n), inv = new Uint8Array(n), zero = 0, metal = 0, body = 0;
        for (let i = 0, j = 0; i < n; i++, j += 4) {
            if (!B[i]) continue;
            body++;
            const cc = S[j + 2];
            if (cc === 0) zero++;
            if (S[j] >= 200) metal++;
            if (cc >= 1 && cc <= 15) none[i] = 1;
            // "inverted" = smooth G under a dull B. Smooth-under-haze is also a designed look (PROTECTED Truchet Glass is
            // M247 G30 B255 by design; holo / ghost / oil-slick finishes sit at B 146-219), so on catalogue spec only the
            // classic typo counts: a NON-metal paint with B >= 240 ("255 = max clearcoat"). Spec the painter authored
            // (ctx.authored: imports, SHOKK DROP plates, Material layer) is held to the plain rule B >= 128.
            else if (S[j + 1] <= t.glossG && ((A && A[i] && cc >= t.dullB) || (cc >= t.pxDullB && S[j] < t.pxMaxM))) inv[i] = 1;
        }
        none = open(none, W, H, 1); inv = open(inv, W, H, 1);
        const c1 = components(none, W, H, T.minArea);
        if (c1.comps.length) {
            const h = keepComps(c1.lab, c1.comps, n);
            let sb = 0, sg = 0, k = 0;
            for (let i = 0; i < n; i++) if (h[i]) { sb += S[i * 4 + 2]; sg += S[i * 4 + 1]; k++; }
            out.push({
                check: 'coat-none', severity: 'high', title: 'Clearcoat Set To ' + Math.round(sb / k) + ' (Means No Coat)',
                why: 'In iRacing a clearcoat of 0 to 15 all mean "no clearcoat", so B ' + Math.round(sb / k) + ' is not a light coat: this area renders bare and flat next to the glossy body.',
                area: k, heat: toHeat(h), regions: regionsOf(h, W, H, T.minArea), stats: { meanB: Math.round(sb / k), meanG: Math.round(sg / k) },
                fixes: [{ id: 'coat16', label: 'Set Clearcoat To 16 (Max Gloss)' }]
            });
        }
        // The same mistake in the painter's own upload (ctx.plates = SHOKK DROP spec plates read verbatim). The engine's iron
        // rule exports B 1-15 as 16, so the TGA never shows it: flag plate pixels with B 1-15 where the plate really landed
        // (rendered M and G match the plate, G after the R >= 15 floor) and the export changed B. foot already excludes
        // pixels the Material layer sets B for, so the Doctor's own "Keep It Full Gloss" fix clears the finding.
        (ctx.plates || []).forEach(function (p) {
            if (!p || !p.spec || p.spec.length !== n * 4) return;
            const src = new Uint8Array(n); let any = 0;
            for (let i = 0, j = 0; i < n; i++, j += 4) {
                if (!B[i] || (p.foot && !p.foot[i])) continue;
                const pb = p.spec[j + 2]; if (pb < 1 || pb > 15) continue;
                const pm = p.spec[j], pg = pm < 240 ? Math.max(15, p.spec[j + 1]) : p.spec[j + 1];
                if (Math.abs(S[j] - pm) > 3 || Math.abs(S[j + 1] - pg) > 3 || S[j + 2] === pb) continue;
                src[i] = 1; any++;
            }
            if (!any) return;
            const cs = components(open(src, W, H, 1), W, H, T.minArea);
            if (!cs.comps.length) return;
            const h = keepComps(cs.lab, cs.comps, n);
            let sb = 0, se = 0, k = 0;
            for (let i = 0; i < n; i++) if (h[i]) { sb += p.spec[i * 4 + 2]; se += S[i * 4 + 2]; k++; }
            const pb = Math.round(sb / k), eb = Math.round(se / k);
            out.push({
                check: 'coat-none', severity: 'high', title: 'Your Spec Upload Says Clearcoat ' + pb + ' (Means No Coat)',
                why: '"' + (p.name || p.id) + '" has B ' + pb + ' here. In iRacing 0 to 15 all mean no clearcoat, not a light coat, and SPB exports 1 to 15 as ' + eb + ' (full gloss), so this area will not match what your old file looked like.',
                area: k, heat: toHeat(h), regions: regionsOf(h, W, H, T.minArea), stats: { plateB: pb, exportB: eb, plate: p.id },
                fixes: [{ id: 'coat16', label: 'Keep It Full Gloss (16)' }]
            });
        });
        const c2 = components(inv, W, H, T.minArea);
        if (c2.comps.length) {   // a typed-in value is a flat fill; a designed finish (holo, glass) varies -> keep flat fills only
            const L = c2.comps[c2.comps.length - 1].id + 1, sb = new Float64Array(L), qb = new Float64Array(L), sg = new Float64Array(L), qg = new Float64Array(L), kk = new Float64Array(L);
            for (let i = 0; i < n; i++) { const l = c2.lab[i]; if (!l || l >= L) continue; const b = S[i * 4 + 2], g = S[i * 4 + 1]; sb[l] += b; qb[l] += b * b; sg[l] += g; qg[l] += g * g; kk[l]++; }
            c2.comps = c2.comps.filter(function (c) {
                const k = kk[c.id]; if (!k) return false;
                const vb = qb[c.id] / k - Math.pow(sb[c.id] / k, 2), vg = qg[c.id] / k - Math.pow(sg[c.id] / k, 2);
                return Math.sqrt(Math.max(0, vb)) <= t.flatStd && Math.sqrt(Math.max(0, vg)) <= t.flatStd;
            });
        }
        if (c2.comps.length) {
            const h = keepComps(c2.lab, c2.comps, n);
            let sb = 0, sg = 0, k = 0;
            for (let i = 0; i < n; i++) if (h[i]) { sb += S[i * 4 + 2]; sg += S[i * 4 + 1]; k++; }
            out.push({
                check: 'coat-inverted', severity: 'medium', title: 'Dull Coat On A Mirror-Smooth Area',
                why: 'Blue runs backwards in iRacing (16 is the glossiest coat, 255 the dullest), so this smooth G ' + Math.round(sg / k) + ' area wears a hazy B ' + Math.round(sb / k) + ' coat; a higher number does not mean more clearcoat.',
                area: k, heat: toHeat(h), regions: regionsOf(h, W, H, T.minArea), stats: { meanB: Math.round(sb / k), meanG: Math.round(sg / k) },
                fixes: [{ id: 'coat16', label: 'Set Clearcoat To 16 (Gloss)' }]
            });
        }
        if (body > 0 && zero / body >= t.zeroFrac && metal / body < 0.5) {
            const h = new Uint8Array(n);
            for (let i = 0, j = 0; i < n; i++, j += 4) if (B[i] && S[j + 2] === 0) h[i] = 255;
            out.push({
                check: 'coat-zero', severity: 'tip', title: 'No Clearcoat Anywhere',
                why: 'B is 0 on almost the whole car, which iRacing reads as no clearcoat at all: fine for a raw or matte build, but a gloss paint job needs B 16.',
                area: zero, heat: h, regions: regionsOf(h, W, H, T.minArea), stats: { zeroFrac: +(zero / body).toFixed(3) },
                fixes: [{ id: 'coat16', label: 'Set Clearcoat To 16 (Max Gloss)' }]
            });
        }
        return out;
    }

    // ------------------------------------------------------------------ C3: decals inherit the body's metal spec
    // ctx.decals = [{ id, name, role, own: Uint8Array (0..255 visible ownership), material: null|string }]
    function checkDecals(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, S = ctx.spec, B = ctx.body, t = T.c3, hits = [];
        const decals = (ctx.decals || []).filter(function (d) { return d && d.own && d.own.length === n && !d.material; });
        if (!decals.length) return null;
        const any = new Uint8Array(n);
        (ctx.decals || []).forEach(function (d) { if (d && d.own && d.own.length === n) for (let i = 0; i < n; i++) if (d.own[i] >= 128) any[i] = 1; });
        const heat = new Uint8Array(n);
        // Judged PER STICKER, not per layer: one "sponsors" layer holds stickers all over the car and only the ones sitting
        // on a chrome panel inherit chrome (owner car: 32% of "Contingency Decals" sits on the panel -> a per-layer metal
        // fraction of 0.32 hid it). Stickers = components of the layer dilated by the ring distance (letters merge).
        decals.forEach(function (d) {
            const inn = new Uint8Array(n);
            let k = 0;
            for (let i = 0; i < n; i++) if (d.own[i] >= 128 && B[i]) { inn[i] = 1; k++; }
            if (k < t.minPx) return;
            const outer = dilate(inn, W, H, t.ring), inner = dilate(inn, W, H, t.gap);
            const g = components(outer, W, H, 0);
            if (!g.comps.length) return;
            const L = g.comps[g.comps.length - 1].id + 1;
            const kin = new Int32Array(L), kmet = new Int32Array(L), kr = new Int32Array(L);
            const hMi = new Uint32Array(L * 256), hGi = new Uint32Array(L * 256), hMr = new Uint32Array(L * 256), hGr = new Uint32Array(L * 256);
            for (let i = 0, j = 0; i < n; i++, j += 4) {
                const l = g.lab[i]; if (!l) continue;
                if (inn[i]) { kin[l]++; if (S[j] >= t.metalM && S[j + 1] <= t.roughG) kmet[l]++; hMi[l * 256 + S[j]]++; hGi[l * 256 + S[j + 1]]++; }
                else if (!inner[i] && B[i] && !any[i]) { kr[l]++; hMr[l * 256 + S[j]]++; hGr[l * 256 + S[j + 1]]++; }
            }
            const hmed = function (h, l, c) { let s = 0; const half = c >> 1; for (let v = 0; v < 256; v++) { s += h[l * 256 + v]; if (s > half) return v; } return 255; };
            const bad = new Uint8Array(L); let px = 0, met = 0, nst = 0, big = 0, bm = 0, bg = 0;
            for (let l = 1; l < L; l++) {
                if (kin[l] < t.minPx || kmet[l] / kin[l] < t.metalFrac || kr[l] < 50) continue;
                const mi = hmed(hMi, l, kin[l]), gi = hmed(hGi, l, kin[l]);
                if (Math.abs(mi - hmed(hMr, l, kr[l])) > t.inheritD || Math.abs(gi - hmed(hGr, l, kr[l])) > t.inheritD) continue;   // its own spec: specced on purpose
                bad[l] = 1; px += kin[l]; met += kmet[l]; nst++;
                if (kin[l] > big) { big = kin[l]; bm = mi; bg = gi; }
            }
            if (!nst) return;
            for (let i = 0; i < n; i++) if (inn[i] && bad[g.lab[i]]) heat[i] = 255;
            hits.push({ id: d.id, name: d.name, role: d.role, px: px, stickers: nst, metalFrac: +(met / px).toFixed(2), medM: bm, medG: bg });
        });
        if (!hits.length) return null;
        const names = hits.map(function (h) { return h.name; });
        return {
            check: 'decal-chrome', severity: 'high', title: (hits.length === 1 ? names[0] : hits.length + ' Decal Layers') + ' Took The Body\'s Chrome',
            why: 'Decals sit on whatever spec is under them, so these ' + (hits[0].role || 'decals') + ' render as mirror-chrome stickers that reflect the sky and wash out at speed; real vinyl is not metal.',
            area: count(heat), heat: heat, regions: regionsOf(heat, W, H, 50), layers: hits,
            fixes: [{ id: 'vinyl-gloss', label: 'Give Them Gloss Vinyl' }, { id: 'vinyl-matte', label: 'Give Them Matte Vinyl' }]
        };
    }

    // ------------------------------------------------------------------ C4: lifeless flat spec (tip only, presets never auto-applied)
    function checkFlat(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, S = ctx.spec, P = ctx.paint, B = ctx.body, t = T.c4;
        let k = 0; const s = [0, 0, 0], q = [0, 0, 0]; let py = 0, pq = 0;
        for (let i = 0, j = 0; i < n; i += 3, j += 12) {     // every 3rd pixel is plenty for a global std
            if (!B[i]) continue;
            k++;
            for (let c = 0; c < 3; c++) { const v = S[j + c]; s[c] += v; q[c] += v * v; }
            const y = (54 * P[j] + 183 * P[j + 1] + 19 * P[j + 2]) >> 8; py += y; pq += y * y;
        }
        if (k < (n / 3) * t.minBody) return null;
        const sd = s.map(function (v, c) { const m = v / k; return Math.sqrt(Math.max(0, q[c] / k - m * m)); });
        const pm = py / k, psd = Math.sqrt(Math.max(0, pq / k - pm * pm));
        if (Math.max(sd[0], sd[1], sd[2]) > t.flatStd || psd < t.artStd) return null;
        const h = new Uint8Array(n);
        for (let i = 0; i < n; i++) if (B[i]) h[i] = 255;
        return {
            check: 'flat', severity: 'tip', title: 'One Material On The Whole Car',
            why: 'Every pixel has the same spec (M ' + Math.round(s[0] / k) + ', G ' + Math.round(s[1] / k) + ', B ' + Math.round(s[2] / k) + '), so in the sim the stripes, numbers and body all shine the same and the livery reads flat.',
            area: count(h), heat: h, regions: [], stats: { std: sd.map(function (v) { return +v.toFixed(2); }), artStd: Math.round(psd) },
            fixes: [{ id: 'preset-matte-decals', label: 'Matte Vinyl Decals', choice: true }, { id: 'preset-satin-body', label: 'Satin Body', choice: true }, { id: 'preset-metallic-body', label: 'Metallic Body', choice: true }]
        };
    }

    // ------------------------------------------------------------------ C5: spec edges offset from the paint edges they belong to
    function edgeMaps(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, P = ctx.paint, S = ctx.spec, t = T.c5;
        const ep = new Uint8Array(n), es = new Uint8Array(n);
        for (let y = 1; y < H - 1; y++) {
            for (let x = 1; x < W - 1; x++) {
                const i = y * W + x, j = i * 4, a = j - 4, b = j + 4, u = j - W * 4, d = j + W * 4;
                let gp = 0, gs = 0;
                for (let c = 0; c < 3; c++) {
                    const gx = P[b + c] - P[a + c], gy = P[d + c] - P[u + c], g = (gx < 0 ? -gx : gx) + (gy < 0 ? -gy : gy);
                    if (g > gp) gp = g;
                    const hx = S[b + c] - S[a + c], hy = S[d + c] - S[u + c], h = (hx < 0 ? -hx : hx) + (hy < 0 ? -hy : hy);
                    if (h > gs) gs = h;
                }
                if (gp >= t.edge) ep[i] = 1;
                if (gs >= t.edge) es[i] = 1;
            }
        }
        return { ep: ep, es: es };
    }
    function checkAlign(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, S = ctx.spec, B = ctx.body, t = T.c5, TS = t.tile, R = t.maxShift;
        const em = edgeMaps(ctx), ep1 = dilate(em.ep, W, H, 1), es = em.es;
        const tx = Math.ceil(W / TS), ty = Math.ceil(H / TS), bad = [];
        const xs = new Int32Array(TS * TS), ys = new Int32Array(TS * TS);
        for (let by = 0; by < ty; by++) {
            for (let bx = 0; bx < tx; bx++) {
                const x0 = bx * TS, y0 = by * TS, x1 = Math.min(W, x0 + TS), y1 = Math.min(H, y0 + TS);
                let k = 0, hit0 = 0;
                for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const i = y * W + x; if (es[i] && B[i]) { xs[k] = x; ys[k] = y; k++; if (ep1[i]) hit0++; } }
                if (k < t.minEdges) continue;
                const f0 = hit0 / k;
                if (f0 >= t.aligned) continue;
                let best = 0, bdx = 0, bdy = 0;
                const step = Math.max(1, Math.floor(k / 400));
                for (let dy = -R; dy <= R; dy++) {
                    for (let dx = -R; dx <= R; dx++) {
                        if (!dx && !dy) continue;
                        let h = 0, m = 0;
                        for (let e = 0; e < k; e += step) {
                            const X = xs[e] - dx, Y = ys[e] - dy; m++;
                            if (X >= 0 && Y >= 0 && X < W && Y < H && ep1[Y * W + X]) h++;
                        }
                        const f = h / m;
                        if (f > best + 1e-9 || (Math.abs(f - best) < 1e-9 && dx * dx + dy * dy < bdx * bdx + bdy * bdy)) { best = f; bdx = dx; bdy = dy; }
                    }
                }
                if (best >= t.best && best - f0 >= t.gain && Math.max(Math.abs(bdx), Math.abs(bdy)) >= t.minShift) bad.push({ bx: bx, by: by, dx: bdx, dy: bdy, f0: +f0.toFixed(2), f: +best.toFixed(2), k: k });
            }
        }
        if (bad.length < t.minTiles) return null;
        // the dominant shift (vote), tiles that agree within 1 px
        const votes = {};
        bad.forEach(function (b) { const key = b.dx + ',' + b.dy; votes[key] = (votes[key] || 0) + 1; });
        const top = Object.keys(votes).sort(function (a, b) { return votes[b] - votes[a]; })[0].split(',').map(Number);
        let agree = bad.filter(function (b) { return Math.abs(b.dx - top[0]) <= 1 && Math.abs(b.dy - top[1]) <= 1; });
        // intent guard (calibrated 2026-10-10): a misregistered mask or spec map displaces a CONTINUOUS edge, so the
        // agreeing tiles form a chain. Designed offsets in periodic patterns (PROTECTED Truchet Glass: 8 tiles at
        // (-5,-5), every one 3 tiles from the next; Hologram Metal: 2 isolated tiles) do not. Keep chains of >= chain
        // tiles, allowing one empty tile of gap (a tile on the edge can fall short of minEdges).
        const par = agree.map(function (_, i) { return i; });
        function root(i) { while (par[i] !== i) { par[i] = par[par[i]]; i = par[i]; } return i; }
        for (let a = 0; a < agree.length; a++) for (let b = a + 1; b < agree.length; b++)   // neighbours within 2 tiles
            if (Math.max(Math.abs(agree[a].bx - agree[b].bx), Math.abs(agree[a].by - agree[b].by)) <= 2) par[root(a)] = root(b);
        const per = {};
        agree.forEach(function (_, i) { const r = root(i); per[r] = (per[r] || 0) + 1; });
        agree = agree.filter(function (_, i) { return per[root(i)] >= t.chain; });
        if (agree.length < t.minTiles) return null;
        const dx = top[0], dy = top[1];
        // halo = pixels whose spec differs from where it should have come from (the band between spec edge and paint edge)
        const tileOn = new Uint8Array(tx * ty);
        agree.forEach(function (b) { tileOn[b.by * tx + b.bx] = 1; });
        let heat = new Uint8Array(n);
        for (let y = 0; y < H; y++) {
            for (let x = 0; x < W; x++) {
                const bxi = (x / TS) | 0, byi = (y / TS) | 0;
                let on = false;
                for (let oy = -1; oy <= 1 && !on; oy++) for (let ox = -1; ox <= 1 && !on; ox++) { const X = bxi + ox, Y = byi + oy; if (X >= 0 && Y >= 0 && X < tx && Y < ty && tileOn[Y * tx + X]) on = true; }
                if (!on) continue;
                const i = y * W + x, X = x + dx, Y = y + dy;
                if (!B[i] || X < 0 || Y < 0 || X >= W || Y >= H) continue;
                const j = i * 4, q = (Y * W + X) * 4;
                const d = Math.max(Math.abs(S[j] - S[q]), Math.abs(S[j + 1] - S[q + 1]), Math.abs(S[j + 2] - S[q + 2]));
                if (d >= t.haloD) heat[i] = 1;
            }
        }
        const area = count(heat);
        if (area < T.minArea / 2) return null;
        const dist = Math.round(Math.sqrt(dx * dx + dy * dy));
        return {
            check: 'misalign', severity: dist >= 4 ? 'high' : 'medium', title: 'Spec Sits ' + dist + ' px Off The Paint',
            why: 'The spec edges are ' + dist + ' px away from the paint edges they belong to, so in iRacing every edge gets a rim of the wrong finish (a shiny halo on matte, a dull one on gloss).',
            area: area, heat: toHeat(heat), regions: regionsOf(heat, W, H, 20), shift: [dx, dy], tiles: agree.length,
            stats: { tiles: agree.map(function (b) { return [b.bx, b.by, b.f0, b.f]; }).slice(0, 40) },
            fixes: [{ id: 'snap-zone', label: 'Snap The Zone Mask Back Into Line' }, { id: 'realign-spec', label: 'Re-Align The Spec Here' }]
        };
    }

    // ------------------------------------------------------------------ C6: distance shimmer (mip chain simulation)
    // The sim minifies the spec through its mip chain. Detail that exists at mip 0 but is gone at mip 1 (the 2x2 average)
    // is what sparkles up close and crawls / flickers while the texture level changes with distance and motion.
    function mipLoss(S, W, H, c) {
        const n = W * H, e = new Int16Array(n);
        for (let y = 0; y < H; y += 2) {
            for (let x = 0; x < W; x += 2) {
                const x1 = Math.min(W - 1, x + 1), y1 = Math.min(H - 1, y + 1);
                const i00 = (y * W + x), i01 = (y * W + x1), i10 = (y1 * W + x), i11 = (y1 * W + x1);
                const m = (S[i00 * 4 + c] + S[i01 * 4 + c] + S[i10 * 4 + c] + S[i11 * 4 + c]) / 4;
                e[i00] = S[i00 * 4 + c] - m; e[i01] = S[i01 * 4 + c] - m; e[i10] = S[i10 * 4 + c] - m; e[i11] = S[i11 * 4 + c] - m;
            }
        }
        return e;
    }
    const LAGS = [[2, 0], [0, 2], [2, 2], [2, -2], [4, 0], [0, 4], [4, 4], [4, -4]];
    function tileStructure(e, W, H, x0, y0, TS) {
        const x1 = Math.min(W, x0 + TS), y1 = Math.min(H, y0 + TS);
        let q = 0;
        for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const v = e[y * W + x]; q += v * v; }
        if (!q) return 0;
        let best = 0;
        for (let l = 0; l < LAGS.length; l++) {
            const dx = LAGS[l][0], dy = LAGS[l][1];
            let s = 0, qa = 0, qb = 0;
            for (let y = y0; y < y1; y++) {
                const Y = y + dy; if (Y < y0 || Y >= y1) continue;
                for (let x = x0; x < x1; x++) {
                    const X = x + dx; if (X < x0 || X >= x1) continue;
                    const a = e[y * W + x], b = e[Y * W + X];
                    s += a * b; qa += a * a; qb += b * b;
                }
            }
            if (qa && qb) { const c = Math.abs(s / Math.sqrt(qa * qb)); if (c > best) best = c; }
        }
        return best;
    }
    function shimmerTiles(ctx) {
        const W = ctx.W, H = ctx.H, S = ctx.spec, B = ctx.body, t = T.c6, TS = t.tile;
        const tx = Math.ceil(W / TS), ty = Math.ceil(H / TS), out = [];
        const eG = mipLoss(S, W, H, 1), eM = mipLoss(S, W, H, 0);
        for (let by = 0; by < ty; by++) {
            for (let bx = 0; bx < tx; bx++) {
                let k = 0, kb = 0, qg = 0, qm = 0, dg = 0, dm = 0;
                for (let y = by * TS; y < Math.min(H, by * TS + TS); y++) {
                    for (let x = bx * TS; x < Math.min(W, bx * TS + TS); x++) {
                        const i = y * W + x; k++;
                        if (!B[i]) continue;
                        kb++;
                        const g = eG[i], m = eM[i];
                        qg += g * g; qm += m * m;
                        if (g >= t.devPx || g <= -t.devPx) dg++;
                        if (m >= t.devPx || m <= -t.devPx) dm++;
                    }
                }
                if (!kb || kb / k < t.minBody) continue;
                const rg = Math.sqrt(qg / kb), rm = Math.sqrt(qm / kb), fg = dg / kb, fm = dm / kb;
                const eg = rg >= t.rms && fg >= t.dens, em = rm >= t.rms && fm >= t.dens;
                // structure: a designed fine texture (brushed grain, weave, flake lattice) repeats; random noise does not.
                // max |normalised autocorrelation| of the mip-1 loss at lags 2 and 4 in 4 directions (white noise ~0).
                const sg = eg ? tileStructure(eG, W, H, bx * TS, by * TS, TS) : 1, sm = em ? tileStructure(eM, W, H, bx * TS, by * TS, TS) : 1;
                // intent guard (calibrated 2026-10-10): every glitter / holo / flake finish is DESIGNED metallic sparkle
                // (M mip-loss rms 23-47 on at_holo_sticker, fo_glitter_ball_rain, efx_spectral_edge, carbon_3k_fine ...).
                // On catalogue spec only roughness noise over a QUIET metallic (Photoshop "Add Noise" on G) counts;
                // spec the painter authored (ctx.authored covers >= authFrac of the tile) is judged on G and M alike.
                let au = 0;
                if (ctx.authored) for (let y = by * TS; y < Math.min(H, by * TS + TS); y++) for (let x = bx * TS; x < Math.min(W, bx * TS + TS); x++) if (ctx.authored[y * W + x]) au++;
                const auth = ctx.authored ? au / k >= t.authFrac : false;
                const ng = eg && sg <= t.struct, nm = em && sm <= t.struct;
                out.push({ bx: bx, by: by, rg: rg, rm: rm, fg: fg, fm: fm, sg: sg, sm: sm, auth: auth, g: ng && (auth || rm < t.quietM), m: nm && auth });
            }
        }
        return { tiles: out, tx: tx, ty: ty };
    }
    function checkShimmer(ctx) {
        const W = ctx.W, H = ctx.H, n = W * H, t = T.c6, TS = t.tile;
        const st = shimmerTiles(ctx);
        const flag = new Uint8Array(st.tx * st.ty);
        let chG = false, chM = false;
        st.tiles.forEach(function (b) { if (b.g || b.m) { flag[b.by * st.tx + b.bx] = 1; chG = chG || b.g; chM = chM || b.m; } });
        const cc = components(flag, st.tx, st.ty, t.minTiles);
        if (!cc.comps.length) return null;
        const keep = keepComps(cc.lab, cc.comps, st.tx * st.ty);
        const heat = new Uint8Array(n);
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (keep[((y / TS) | 0) * st.tx + ((x / TS) | 0)] && ctx.body[y * W + x]) heat[y * W + x] = 255;
        let rg = 0, rm = 0, k = 0;
        st.tiles.forEach(function (b) { if (keep[b.by * st.tx + b.bx]) { rg += b.rg; rm += b.rm; k++; } });
        const chans = (chG ? ['G'] : []).concat(chM ? ['M'] : []);
        return {
            check: 'shimmer', severity: 'medium', title: 'Pixel Noise In ' + (chans.join(' + ') === 'G' ? 'Roughness' : chans.join(' + ') === 'M' ? 'Metallic' : 'Roughness + Metallic') + ' Will Shimmer',
            why: 'Single-pixel spec noise does not survive iRacing\'s mipmaps: up close it sparkles, at distance it averages away, so it crawls and flickers as the car moves and the texture level changes.',
            area: count(heat), heat: heat, regions: regionsOf(heat, W, H, T.minArea), channels: chans,
            stats: { tiles: k, mip1LossRmsG: +(rg / k).toFixed(1), mip1LossRmsM: +(rm / k).toFixed(1) },
            fixes: [{ id: 'soften', label: 'Soften Spec Noise Here' }]
        };
    }

    // ------------------------------------------------------------------ analyze
    const CHECKS = ['chrome-dark', 'coat', 'decal-chrome', 'flat', 'misalign', 'shimmer'];
    function analyze(input, opts) {
        const o = opts || {}, t0 = Date.now();
        const W = input.W, H = input.H, n = W * H;
        if (!W || !H || !input.paint || !input.spec || input.paint.length < n * 4 || input.spec.length < n * 4) throw Error('Spec Doctor needs paint + spec RGBA at the same size');
        // authored (optional Uint8Array W*H): 1 where the spec came from the painter's own values (imported spec map,
        // SHOKK DROP authored plate, Material layer) rather than a catalogue finish. Absent = catalogue rules only.
        const ctx = { W: W, H: H, paint: input.paint, spec: input.spec, body: bodyOf(input.body, n), decals: input.decals || [],
            authored: (input.authored && input.authored.length === n) ? input.authored : null,
            plates: (input.plates || []).filter(function (p) { return p && p.spec && p.spec.length === n * 4; }) };
        const only = o.only ? new Set(o.only) : null, findings = [], ms = {};
        function run(name, fn) {
            if (only && !only.has(name)) return;
            const a = Date.now();
            let r = null;
            try { r = fn(ctx); } catch (e) { r = null; ms[name + ':error'] = String(e && e.message || e); }
            ms[name] = Date.now() - a;
            (Array.isArray(r) ? r : (r ? [r] : [])).forEach(function (f) { findings.push(f); });
        }
        run('chrome-dark', checkChromeDark);
        run('coat', checkClearcoat);
        run('decal-chrome', checkDecals);
        run('flat', checkFlat);
        run('misalign', checkAlign);
        run('shimmer', checkShimmer);
        const rank = { high: 0, medium: 1, tip: 2 };
        findings.sort(function (a, b) { return rank[a.severity] - rank[b.severity] || b.area - a.area; });
        findings.forEach(function (f, i) { f.key = f.check + ':' + (f.regions && f.regions[0] ? f.regions[0].bbox.join(',') : i); });
        return { version: VERSION, W: W, H: H, findings: findings, ms: ms, total_ms: Date.now() - t0 };
    }

    // ------------------------------------------------------------------ fix maths (pure): patches the tools then apply
    // A spec patch: { bbox:[x0,y0,x1,y1], val: Uint8Array(bw*bh*3) M,R,CC, cov: Uint8Array(bw*bh*3) } (full-res pixels)
    function feather(heat, W, H, r) {          // 0..255 soft mask: 255 inside, ramps down over r px outside
        if (!r) return heat;
        const m = new Uint8Array(W * H); for (let i = 0; i < m.length; i++) m[i] = heat[i] ? 1 : 0;
        const f = boxMean(dilate(m, W, H, r), W, H, r), out = new Uint8Array(W * H);
        for (let i = 0; i < out.length; i++) out[i] = heat[i] ? 255 : Math.round(Math.min(1, f[i]) * 255);
        return out;
    }
    function patchFrom(mask, W, H, fn) {
        const bb = bboxOf(mask, W, H); if (!bb) return null;
        const bw = bb[2] - bb[0], bh = bb[3] - bb[1], val = new Uint8Array(bw * bh * 3), cov = new Uint8Array(bw * bh * 3);
        for (let y = bb[1]; y < bb[3]; y++) for (let x = bb[0]; x < bb[2]; x++) {
            const i = y * W + x, a = mask[i]; if (!a) continue;
            fn(i, (y - bb[1]) * bw + (x - bb[0]), a, val, cov);
        }
        return { bbox: bb, val: val, cov: cov };
    }
    function specSet(spec, mask, W, H, setv) {   // setv = [M|null, R|null, CC|null]
        return patchFrom(mask, W, H, function (i, o, a, val, cov) {
            for (let c = 0; c < 3; c++) if (setv[c] != null) { val[o * 3 + c] = setv[c]; cov[o * 3 + c] = a; }
        });
    }
    function specBlur(spec, mask, W, H, chans, r) {   // chans e.g. [1] (G) or [0,1]
        const n = W * H, out = {};
        chans.forEach(function (c) {
            const ch = new Float32Array(n); for (let i = 0; i < n; i++) ch[i] = spec[i * 4 + c];
            out[c] = boxMean(boxMean(ch, W, H, r || 1), W, H, r || 1);
        });
        return patchFrom(mask, W, H, function (i, o, a, val, cov) {
            chans.forEach(function (c) { val[o * 3 + c] = Math.max(0, Math.min(255, Math.round(out[c][i]))); cov[o * 3 + c] = a; });
        });
    }
    function specShift(spec, mask, W, H, dx, dy) {   // corrected(x) = observed(x + shift)
        return patchFrom(mask, W, H, function (i, o, a, val, cov) {
            const x = i % W, y = (i / W) | 0, X = Math.max(0, Math.min(W - 1, x + dx)), Y = Math.max(0, Math.min(H - 1, y + dy)), q = (Y * W + X) * 4;
            for (let c = 0; c < 3; c++) { val[o * 3 + c] = spec[q + c]; cov[o * 3 + c] = a; }
        });
    }
    // paint lift: keep hue AND the art. The region's mean brightness moves to `target`; every pixel keeps its offset from
    // that mean (x LIFT_GAIN, since detail squeezed into V 0-40 needs more swing to read at V 200), so a textured black
    // panel (hex / carbon / grain) becomes the same texture in light grey, not a flat slab.
    // [REV-DOCTOR 2026-10-10e] v1 set every pixel to V = target: the planted hex art (V sd 11.4) came out as flat grey on
    // the RENDER TGA (sheet_findings.png row 1). Near-black with no hue -> neutral grey at the lifted value.
    const LIFT_GAIN = 1.5;
    function paintLift(paint, mask, W, H, target) {
        const bb = bboxOf(mask, W, H); if (!bb) return null;
        const bw = bb[2] - bb[0], bh = bb[3] - bb[1], val = new Uint8Array(bw * bh * 3), cov = new Uint8Array(bw * bh);
        let sv = 0, sa = 0;
        for (let y = bb[1]; y < bb[3]; y++) for (let x = bb[0]; x < bb[2]; x++) {
            const i = y * W + x, a = mask[i]; if (!a) continue;
            const j = i * 4; sv += a * Math.max(paint[j], paint[j + 1], paint[j + 2]); sa += a;
        }
        const mu = sa ? sv / sa : 0;
        for (let y = bb[1]; y < bb[3]; y++) for (let x = bb[0]; x < bb[2]; x++) {
            const i = y * W + x, a = mask[i]; if (!a) continue;
            const j = i * 4, o = (y - bb[1]) * bw + (x - bb[0]), r = paint[j], g = paint[j + 1], b = paint[j + 2];
            const v = Math.max(r, g, b), mn = Math.min(r, g, b);
            const tv = Math.max(8, Math.min(255, target + (v - mu) * LIFT_GAIN));
            let R, G, Bv;
            if (v < 12 || v - mn < 6) { R = G = Bv = tv; }
            else { const k = tv / v; R = r * k; G = g * k; Bv = b * k; }
            val[o * 3] = Math.min(255, Math.round(R)); val[o * 3 + 1] = Math.min(255, Math.round(G)); val[o * 3 + 2] = Math.min(255, Math.round(Bv));
            cov[o] = a;
        }
        return { bbox: bb, val: val, cov: cov };
    }
    // edge overlap of a candidate source mask (e.g. a zone's regionMask) with the misaligned spec edges -> attribution
    function maskEdgeShiftScore(mask, W, H, ctxSpecEdges, dx, dy) {
        const n = W * H, me = new Uint8Array(n);
        for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
            const i = y * W + x, v = mask[i] ? 1 : 0;
            if ((mask[i - 1] ? 1 : 0) !== v || (mask[i + 1] ? 1 : 0) !== v || (mask[i - W] ? 1 : 0) !== v || (mask[i + W] ? 1 : 0) !== v) me[i] = 1;
        }
        const me1 = dilate(me, W, H, 1);
        let k = 0, h = 0;
        for (let i = 0; i < n; i++) if (ctxSpecEdges[i]) { k++; if (me1[i]) h++; }
        return k ? h / k : 0;
    }
    function shiftMask(mask, W, H, dx, dy) {     // out(x) = mask(x + d)  (moves content by -d)
        const out = new Uint8Array(W * H);
        for (let y = 0; y < H; y++) { const Y = y + dy; if (Y < 0 || Y >= H) continue; for (let x = 0; x < W; x++) { const X = x + dx; if (X >= 0 && X < W) out[y * W + x] = mask[Y * W + X]; } }
        return out;
    }

    return {
        version: VERSION, T: T, CHECKS: CHECKS, analyze: analyze,
        checkChromeDark: checkChromeDark, checkClearcoat: checkClearcoat, checkDecals: checkDecals, checkFlat: checkFlat, checkAlign: checkAlign, checkShimmer: checkShimmer,
        shimmerTiles: shimmerTiles, edgeMaps: edgeMaps, mipLoss: mipLoss,
        feather: feather, specSet: specSet, specBlur: specBlur, specShift: specShift, paintLift: paintLift,
        maskEdgeShiftScore: maskEdgeShiftScore, shiftMask: shiftMask,
        _p: { boxMean: boxMean, dilate: dilate, erode: erode, open: open, components: components, bboxOf: bboxOf, count: count, bodyOf: bodyOf }
    };
});
