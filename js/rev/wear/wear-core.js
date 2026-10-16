/* [SPB-REV-WEAR 2026-10-10] Race Wear Studio - core: a race-worn look placed by the CAR's geometry, paint + spec in lockstep.
 *
 * Lane REV-WEAR (orchestrator brief 2026-10-10 08:15). Nobody else can do this because nobody else knows where each pixel of the flat
 * iRacing sheet sits on the car. We reuse REV-FADE's car space (js/rev/fade/fade-space.js, SpbRevFade.build()): every paintable pixel gets
 *   u 0 nose .. 1 tail, z 0 sill .. 1 roof, a arc length from the sill (px), plus its part (left / right side, hood, roof, trunk, bumpers, spoiler).
 * The wheel arches are MEASURED in each side panel's own mask (the bottom edge's semicircle cut-outs, per nose->tail bin), so dirt and spray
 * rise behind the real wheels and brake dust rings the real arches. Left and right use the same physics with different random detail
 * (never mirrored copies); the oval preset puts wall contact on the RIGHT side (oval cars turn left).
 *
 * Classes (each writes paint AND spec; iRacing spec R = metallic, G = roughness (0 mirror), B = clearcoat (0-15 none, 16 max gloss, 255 dull)):
 *   dust / road film  M 0   R 215 CC 200      mud cake        M 0   R 240 CC 255     spray droplets  (dust / mud values)
 *   brake dust        M 70  R 190 CC 170      rubber          M 0   R 235 CC 0  (no clear, hard edge)
 *   wall scuff        M 0   R 210 CC 220      bug splats      M 0   R 120 CC 110
 *   chip to primer    M 0   R 200 CC 0  (hard)   chip to bare metal  M 225 R 110 CC 0 (hard)   speed tape  M 200 R 70 CC 0 (hard)
 *   dulled clear      a DELTA on the clearcoat (+R), applied only where the car already has clear (CC >= 16): it can never land in 1..15.
 * Every class with CC < 16 has a hard spec edge (coverage 0 or 1) and the final CC is snapped out of 1..15 (snap()), here and in the engine.
 *
 * Texture: >= 3 frequency bands everywhere - per-pixel grain, 2 / 8 / 32 / 128 px lattice noise and airflow streaks (36x3 and 140x10 px,
 * aligned with each part's nose->tail direction on the sheet). Marks (chips, splats, droplets, rubber) are 1-12 px stamps. Placement is
 * monotone in "laps": the candidate list is fixed per seed and each mark appears at its own threshold, so more laps ADD wear, never reshuffle.
 *
 * Output (generate): full-sheet buffers pv (RGB) + pc (paint coverage), sv (M,R,CC) + sc (spec coverage), dc (clearcoat dulling delta), bbox.
 * The engine applies them with engine/rev_wear_layer.py (dull first, then out = base*(1-cov) + val*cov), LAST, after every zone, the
 * Material / Fade post-passes and the iron floors, so it sits on top of decals (dirt covers vinyl) exactly as the preview overlay shows.
 *
 * KILL SWITCH: window.SPB_REV_WEAR_OFF = true or localStorage SPB_REV_WEAR_OFF = '1' -> off() true, no UI, no payload (engine: env SPB_REV_WEAR_OFF=1).
 */
(function (root) {
    'use strict';
    const VER = 'wear1.0';

    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_WEAR_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_WEAR_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_WEAR_OFF); }
    }

    // ---------------------------------------------------------------- materials (paint colour + iRacing spec M, R, CC)
    const MAT = {
        dust:   { col: [118, 106, 90],  spec: [0, 215, 200] },
        clay:   { col: [108, 72, 42],   spec: [0, 225, 230] },
        claydry:{ col: [174, 136, 90],  spec: [0, 240, 255] },
        brake:  { col: [52, 42, 34],    spec: [70, 190, 170] },
        rubber: { col: [22, 22, 24],    spec: [0, 235, 0] },
        wall:   { col: [214, 212, 206], spec: [0, 210, 220] },
        primer: { col: [176, 178, 180], spec: [0, 200, 0] },
        primerD:{ col: [92, 96, 100],   spec: [0, 205, 0] },
        metal:  { col: [168, 172, 178], spec: [225, 110, 0] },
        tape:   { col: [196, 198, 201], spec: [200, 70, 0] },
        heat:   { col: [140, 104, 58],  spec: null }
    };
    const BUGS = [[196, 186, 112], [170, 166, 96], [118, 126, 64], [78, 64, 46], [210, 204, 160], [140, 72, 50]];   // beige / yellow-green / dark, red rare

    // ---------------------------------------------------------------- presets: gains per class (0..1+), laps range, label
    const PRESETS = [
        { id: 'showroom', name: 'Showroom', unit: 'laps', max: 60, def: 35, dust: [112, 106, 98], tip: 'A light touch: a slightly dulled clear and a few stone chips on the nose.',
          g: { dull: 0.45, chips: 0.18, dust: 0.08, spray: 0.04, brake: 0.08, rubber: 0, wall: 0, bugs: 0.05, mud: 0, tape: 0, heat: 0, pits: 0.5, scuff: 0 } },
        { id: 'oval', name: 'Short-Track Oval', unit: 'laps', max: 500, def: 55, dust: [70, 66, 60], tip: 'Door rubs and tyre donuts at door height, right-side wall contact (oval cars turn left), dust behind the wheels.',
          g: { dull: 0.6, chips: 0.35, dust: 0.38, spray: 0.4, brake: 0.35, rubber: 1, wall: 1, bugs: 0.15, mud: 0, tape: 0, heat: 0.2, pits: 0.3, scuff: 0.55 } },
        { id: 'road', name: 'Road Course', unit: 'laps', max: 120, def: 55, dust: [98, 90, 78], tip: 'Brake dust round the arches, gravel chips on the nose and lower sides, a little kerb rubber.',
          g: { dull: 0.65, chips: 1, dust: 0.32, spray: 0.45, brake: 1, rubber: 0.25, wall: 0, bugs: 0.35, mud: 0, tape: 0, heat: 0.45, pits: 1, scuff: 0.7 } },
        { id: 'dirt', name: 'Dirt Late Model', unit: 'laps', max: 100, def: 55, dust: [116, 88, 58], tip: 'Mud spray rising behind the wheels, caked lower panels, splatter up the sides, a dusty film everywhere.',
          g: { dull: 0.85, chips: 0.25, dust: 1, spray: 1, brake: 0.15, rubber: 0.1, wall: 0, bugs: 0, mud: 1, tape: 0, heat: 0.2, pits: 0.2, scuff: 0.4 } },
        { id: 'endurance', name: 'Endurance 24 h', unit: 'h', max: 24, def: 60, dust: [86, 80, 70], tip: 'Bugs on the nose, hood and roof edge, heavy brake dust, speed tape on the nose, heat haze on the hood.',
          g: { dull: 0.8, chips: 0.6, dust: 0.5, spray: 0.55, brake: 1, rubber: 0.3, wall: 0, bugs: 1, mud: 0, tape: 1, heat: 0.8, pits: 0.8, scuff: 0.55 } }
    ];
    function preset(id) { return PRESETS.find(p => p.id === id) || PRESETS[1]; }
    function lapsText(id, v) { const p = preset(id), n = Math.round(p.max * Math.max(0, Math.min(100, v)) / 100); return p.unit === 'h' ? n + ' h' : n + ' laps'; }

    // ---------------------------------------------------------------- random + noise (deterministic, seedable)
    function mulberry(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function h3(a, b, s) { let h = (Math.imul(a, 374761393) + Math.imul(b, 668265263) + Math.imul(s, 1442695041)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return (h >>> 0) / 4294967296; }
    // lattice value noise over the whole sheet, cell cx x cy px, smoothstep bilinear -> Uint8Array (0..255). ~25 ms at 2048^2.
    // (2026-10-10 v2: one lattice alone showed its grid at 1:1 - square mud blotches, rectangular streak blocks. Every field is now the mean of
    //  two lattices with unrelated cell sizes + offsets, and the shape fields are read through a domain warp in generate(): organic edges.)
    function lattice(W, H, cx, cy, seed, ox, oy, into, wgt) {
        ox = ox || 0; oy = oy || 0;
        const gw = Math.ceil((W + ox) / cx) + 2, gh = Math.ceil((H + oy) / cy) + 2, L = new Float32Array(gw * gh);
        for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) L[j * gw + i] = h3(i, j, seed);
        const ix = new Int32Array(W), fx = new Float32Array(W), iy = new Int32Array(H), fy = new Float32Array(H);
        for (let x = 0; x < W; x++) { const t = (x + ox) / cx, i = t | 0, f = t - i; ix[x] = i; fx[x] = f * f * (3 - 2 * f); }
        for (let y = 0; y < H; y++) { const t = (y + oy) / cy, i = t | 0, f = t - i; iy[y] = i; fy[y] = f * f * (3 - 2 * f); }
        const out = into || new Float32Array(W * H), w = wgt == null ? 1 : wgt;
        for (let y = 0; y < H; y++) {
            const r0 = iy[y] * gw, r1 = r0 + gw, g = fy[y], o = y * W;
            for (let x = 0; x < W; x++) {
                const i = ix[x], f = fx[x], a0 = L[r0 + i], b0 = L[r1 + i];
                const a = a0 + (L[r0 + i + 1] - a0) * f, b = b0 + (L[r1 + i + 1] - b0) * f;
                out[o + x] += (a + (b - a) * g) * w;
            }
        }
        return out;
    }
    function lat2(W, H, cx, cy, seed) {   // two lattices (cells c and 0.71c, offset) -> contrast-restored Uint8 field
        const acc = new Float32Array(W * H);
        lattice(W, H, cx, cy, seed, 0, 0, acc, 0.5); lattice(W, H, cx * 0.71, cy * 0.71, seed + 101, cx * 0.37, cy * 0.61, acc, 0.5);
        const out = new Uint8Array(W * H);
        for (let i = 0; i < acc.length; i++) { const v = (acc[i] - 0.5) * 1.6 + 0.5; out[i] = v <= 0 ? 0 : (v >= 1 ? 255 : v * 255); }
        return out;
    }
    const FIELD = { key: null, f: null };
    function fields(W, H, seed, needV) {
        const key = W + 'x' + H + ':' + seed + ':' + (needV ? 1 : 0);
        if (FIELD.key === key) return FIELD.f;
        const s = seed * 7 + 11, f = {
            n2: lat2(W, H, 2.3, 2.3, s + 1), n8: lat2(W, H, 8, 8, s + 2), n32: lat2(W, H, 32, 32, s + 3), n128: lat2(W, H, 128, 128, s + 4),
            sh1: lat2(W, H, 36, 3, s + 5), sh2: lat2(W, H, 140, 10, s + 6), wx: lat2(W, H, 61, 61, s + 9), wy: lat2(W, H, 61, 61, s + 10)
        };
        if (needV) { f.sv1 = lat2(W, H, 3, 36, s + 7); f.sv2 = lat2(W, H, 10, 140, s + 8); }
        FIELD.key = key; FIELD.f = f; return f;
    }

    // ---------------------------------------------------------------- car geometry: wheel arches + per-part frames
    // Arches are measured on each SIDE panel: per nose->tail bin, how many panel pixels it has (the arch cut-out removes the bottom of the column).
    // Car-surface px: X = u * L (along the car), Y = a (up from the sill). Fallback: typical stock-car arches at u 0.2 / 0.8.
    function sideFrame(sp, r) {
        const NB = 96, cnt = new Float32Array(NB), bot = new Float32Array(NB).fill(1e9);
        for (let k = 0; k < r.mask.length; k += 2) {
            if (!r.mask[k]) continue;
            const b = Math.max(0, Math.min(NB - 1, (r.U[k] * NB) | 0)); cnt[b]++; if (r.A[k] < bot[b]) bot[b] = r.A[k];
        }
        const nz = Array.from(cnt).filter(v => v > 0).sort((a, b) => a - b), p75 = nz.length ? nz[Math.floor(nz.length * 0.75)] : 0;
        let xs = -1, xe = -1; for (let i = 0; i < NB; i++) if (cnt[i] >= 0.15 * p75) { if (xs < 0) xs = i; xe = i + 1; }
        const runs = []; let cur = null, gap = 0;
        for (let i = xs; i < xe; i++) {
            const isA = cnt[i] < 0.8 * p75;
            if (isA) { if (!cur) cur = { a: i, b: i + 1 }; else cur.b = i + 1; gap = 0; } else if (cur) { if (++gap > 1) { runs.push(cur); cur = null; gap = 0; } }
        }
        if (cur) runs.push(cur);
        const minW = Math.max(3, Math.round(0.04 * (xe - xs)));
        let rr = runs.filter(q => (q.b - q.a) >= minW && q.a > xs + 1).sort((p, q) => (q.b - q.a) - (p.b - p.a)).slice(0, 2).sort((p, q) => p.a - q.a);
        const sills = Array.from(bot).filter(v => v < 1e8).sort((a, b) => a - b), sill = sills.length ? sills[Math.floor(sills.length * 0.2)] : 0;
        const L = sp.L, arches = [];
        let measured = rr.length === 2 && (rr[1].a - rr[0].b) >= 0.2 * (xe - xs);
        if (measured) {
            const w0 = (rr[0].b - rr[0].a) / NB * L;
            rr.forEach((q, i) => {
                let w = (q.b - q.a) / NB * L; if (i === 1) w = Math.min(w, 1.15 * w0);   // the tail taper can merge with the rear arch
                const x0 = q.a / NB * L; arches.push({ xc: x0 + w / 2, r: w / 2, yc: sill });
            });
        } else {
            [0.2, 0.8].forEach(u => arches.push({ xc: u * L, r: 0.07 * L, yc: sill }));
        }
        return { arches, measured, sill };
    }
    function topFrame(r) {
        let mn = 1e9, mx = -1e9;
        for (let k = 0; k < r.mask.length; k += 3) if (r.mask[k]) { const u = r.U[k]; if (u < mn) mn = u; if (u > mx) mx = u; }
        return { umin: mn, umax: Math.max(mn + 1e-4, mx) };
    }
    function flowDir(r) { // mean sheet direction of +u (towards the tail) -> unit vector or [0,0]
        let gx = 0, gy = 0, n = 0;
        for (let y = 0; y < r.h - 3; y += 3) for (let x = 0; x < r.w - 3; x += 3) {
            const k = y * r.w + x; if (!r.mask[k] || !r.mask[k + 3] || !r.mask[k + 3 * r.w]) continue;
            gx += r.U[k + 3] - r.U[k]; gy += r.U[k + 3 * r.w] - r.U[k]; n++;
        }
        const m = Math.hypot(gx, gy) / Math.max(1, n);
        if (m < 1e-5) return [0, 0];
        const l = Math.hypot(gx, gy); return [gx / l, gy / l];
    }
    function geometry(sp) {
        if (sp._wearGeo) return sp._wearGeo;
        const g = { parts: {}, vertical: false };
        sp.order.forEach(n => {
            const r = sp.parts[n]; if (!r || r.skip) return;
            const o = { name: n, kind: r.kind, flow: flowDir(r), side: /left/i.test(n) ? 'L' : (/right/i.test(n) ? 'R' : null) };
            if (r.kind === 'side') Object.assign(o, sideFrame(sp, r));
            else Object.assign(o, topFrame(r));
            o.isHood = /hood/i.test(n); o.isRoof = /roof|cab/i.test(n); o.isTrunk = /trunk|deck|bed/i.test(n);
            if (Math.abs(o.flow[1]) > Math.abs(o.flow[0])) g.vertical = true;
            g.parts[n] = o;
        });
        // the side that failed to measure borrows the other's arches (both sides are registered into the same u frame)
        const sides = Object.values(g.parts).filter(o => o.kind === 'side');
        const good = sides.find(o => o.measured);
        sides.forEach(o => { if (!o.measured && good) o.arches = good.arches.map(a => ({ xc: a.xc, r: a.r, yc: o.sill })); });
        sp._wearGeo = g; return g;
    }

    // ---------------------------------------------------------------- compositing helpers (premultiplied over, per pixel)
    function smooth(e0, e1, x) { const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); }
    function snapCC(v) { return (v >= 1 && v < 16) ? (v < 8 ? 0 : 16) : v; }   // never land in 1..15 by accident

    // B: the output buffers. Paint and spec are premultiplied accumulators (float) -> resolved to val / cov at the end.
    function Buf(W, H) {
        const N = W * H;
        return { W, H, pp: new Float32Array(N * 3), pa: new Float32Array(N), sp: new Float32Array(N * 3), sa: new Float32Array(N), dc: new Float32Array(N), x0: W, y0: H, x1: -1, y1: -1 };
    }
    function over(B, i, col, ca, spec, sa) {
        if (ca > 0) {
            const k = 1 - ca, o = i * 3; B.pp[o] = B.pp[o] * k + col[0] * ca; B.pp[o + 1] = B.pp[o + 1] * k + col[1] * ca; B.pp[o + 2] = B.pp[o + 2] * k + col[2] * ca;
            B.pa[i] = B.pa[i] * k + ca;
        }
        if (spec && sa > 0) {
            const k = 1 - sa, o = i * 3; B.sp[o] = B.sp[o] * k + spec[0] * sa; B.sp[o + 1] = B.sp[o + 1] * k + spec[1] * sa; B.sp[o + 2] = B.sp[o + 2] * k + spec[2] * sa;
            B.sa[i] = B.sa[i] * k + sa;
        }
    }

    // ---------------------------------------------------------------- [REV-WEAR2 2026-10-10] edge feather
    // Wear used to stop dead at the part mask (template holes, wheel openings, panel edges): coverage 0.8 on one pixel, 0 on the next - a visible hard cut in the dirt
    // (ARCA / truck sheets at 1:1). Now every part pixel is scaled by smoothstep(0.5, 3.5, d) where d = chamfer distance (px) to the nearest NON-part pixel
    // (sheet border counts as non-part): 1 px in = 7 %, 2 px = 50 %, 3 px = 93 %, 3.5+ px = 100 %. 3-4 chamfer, two raster passes (~50 ms at 2048^2).
    function edgeFeather(owner, W, H) {
        const N = W * H, d = new Uint8Array(N);
        for (let i = 0; i < N; i++) d[i] = owner[i] ? 255 : 0;
        for (let y = 0; y < H; y++) {
            const o = y * W;
            for (let x = 0; x < W; x++) {
                const i = o + x; let v = d[i]; if (!v) continue;
                const l = x > 0 ? d[i - 1] : 0, u = y > 0 ? d[i - W] : 0, ul = (x > 0 && y > 0) ? d[i - W - 1] : 0, ur = (x < W - 1 && y > 0) ? d[i - W + 1] : 0;
                const a = l + 3, b = u + 3, c = ul + 4, e = ur + 4;
                if (a < v) v = a; if (b < v) v = b; if (c < v) v = c; if (e < v) v = e;
                d[i] = v;
            }
        }
        const lut = new Uint8Array(256);
        for (let k = 0; k < 256; k++) { const t = Math.max(0, Math.min(1, (k / 3 - 0.5) / 3)); lut[k] = Math.round(255 * t * t * (3 - 2 * t)); }
        for (let y = H - 1; y >= 0; y--) {
            const o = y * W;
            for (let x = W - 1; x >= 0; x--) {
                const i = o + x; let v = d[i]; if (!v) continue;
                const r = x < W - 1 ? d[i + 1] : 0, dn = y < H - 1 ? d[i + W] : 0, dl = (x > 0 && y < H - 1) ? d[i + W - 1] : 0, dr = (x < W - 1 && y < H - 1) ? d[i + W + 1] : 0;
                const a = r + 3, b = dn + 3, c = dl + 4, e = dr + 4;
                if (a < v) v = a; if (b < v) v = b; if (c < v) v = c; if (e < v) v = e;
                d[i] = v;
            }
        }
        for (let i = 0; i < N; i++) d[i] = lut[d[i]];
        return d;
    }

    // ---------------------------------------------------------------- stamps (1..12 px marks)
    function stampChip(B, mask, x, y, rad, rnd, metal, gain, dark, v2) {
        const W = B.W, H = B.H, p1 = rnd() * 6.28, p2 = rnd() * 6.28, a1 = 0.22 + rnd() * 0.18, a2 = 0.1 + rnd() * 0.12, R = Math.ceil(rad * (v2 ? 1.9 : 1.5)) + 1;
        const prim = dark ? MAT.primerD : MAT.primer;
        // [REV-WEAR2 2026-10-10] v2 shape: the old 3-lobe harmonic (amplitude up to 0.4) made every chip a triangle - confetti at 1:1. Now an irregular ROUND pit:
        // an ellipse (random elongation) with 2/4/5/7/9-lobe ragged edge, plus a thin lifted-paint rim in the dark primer around it. Same 4 random draws as before
        // (the other harmonics are derived from them), so bugs / droplets downstream of the chips land where they did.
        const p3 = (p1 * 7.31 + p2 * 3.17) % 6.2832, p4 = (p2 * 5.13 + p1 * 1.91) % 6.2832, el = 0.1 + 0.35 * a2 * 4, ph = p3;
        for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
            const px = x + dx, py = y + dy; if (px < 0 || py < 0 || px >= W || py >= H) continue;
            const i = py * W + px; if (!mask(i)) continue;
            const th = Math.atan2(dy, dx), d = Math.hypot(dx, dy);
            if (v2) {
                const rr = rad * (1 + el * Math.cos(2 * (th - ph)) * 0.45 + 0.07 * Math.sin(3 * th + p1) + 0.05 * Math.sin(5 * th + p2) + 0.045 * Math.sin(8 * th + p3) + 0.03 * Math.sin(13 * th + p4));   // round + ragged: v2a (lobes 0.1-0.2 deep) read as stars
                const c2 = Math.max(0, Math.min(1, rr - d + 0.5)) * gain;
                if (c2 > 0) {
                    over(B, i, prim.col, c2, prim.spec, c2 >= 0.5 ? 1 : 0);
                    if (metal && d < rr * 0.55) { const cm = Math.max(0, Math.min(1, rr * 0.55 - d + 0.5)) * gain; over(B, i, MAT.metal.col, cm, MAT.metal.spec, cm >= 0.5 ? 1 : 0); }
                    mark(B, px, py);
                } else {
                    const rim = Math.max(0, Math.min(1, rr + 1.15 - d + 0.5)) * 0.42 * gain * (0.55 + 0.45 * Math.sin(11 * th + p3));   // lifted paint edge
                    if (rim > 0.04) { over(B, i, MAT.primerD.col, rim, null, 0); mark(B, px, py); }
                }
                continue;
            }
            const rr = rad * (1 + a1 * Math.sin(3 * th + p1) + a2 * Math.sin(5 * th + p2));
            const c = Math.max(0, Math.min(1, rr - d + 0.5)) * gain; if (c <= 0) continue;
            const hard = c >= 0.5 ? 1 : 0;
            over(B, i, prim.col, c, prim.spec, hard);
            if (metal && d < rr * 0.55) { const cm = Math.max(0, Math.min(1, rr * 0.55 - d + 0.5)) * gain; over(B, i, MAT.metal.col, cm, MAT.metal.spec, cm >= 0.5 ? 1 : 0); }
            mark(B, px, py);
        }
    }
    function stampBlob(B, mask, x, y, rx, ry, dir, col, spec, alpha, rnd, tail) {
        // an ellipse (rx along dir, ry across) with a ragged edge + optional smear tail (length tail * rx) towards +dir; soft edge
        const W = B.W, H = B.H, ux = dir[0] || 1, uy = dir[1] || 0, R = Math.ceil(Math.max(rx * (1 + (tail || 0)), ry) * 1.4) + 1, p1 = rnd() * 6.28, p2 = rnd() * 6.28, a1 = 0.1 + rnd() * 0.12;
        for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
            const px = x + dx, py = y + dy; if (px < 0 || py < 0 || px >= W || py >= H) continue;
            const i = py * W + px; if (!mask(i)) continue;
            const s = dx * ux + dy * uy, t = -dx * uy + dy * ux;
            let c = 0;
            const th = Math.atan2(t, s), e = Math.hypot(s / rx, t / ry) * (1 - a1 * Math.sin(3 * th + p1) - a1 * 0.6 * Math.sin(5 * th + p2));
            c = Math.max(0, Math.min(1, (1 - e) * Math.min(rx, ry) + 0.5));
            if (tail && s > 0) { // smear: narrowing, fading streak behind the core
                const L = tail * rx, q = s / L; if (q < 1) { const wv = ry * (1 - q) * 0.75 + 0.35, ct = Math.max(0, Math.min(1, wv - Math.abs(t) + 0.5)) * (1 - q) * 0.85; if (ct > c) c = ct; }
            }
            c *= alpha; if (c <= 0.01) continue;
            over(B, i, col, c, spec, c); mark(B, px, py);
        }
    }
    function mark(B, x, y) { if (x < B.x0) B.x0 = x; if (y < B.y0) B.y0 = y; if (x > B.x1) B.x1 = x; if (y > B.y1) B.y1 = y; }

    // ---------------------------------------------------------------- the generator
    // rec: { preset, laps (0..100), seed, opacity (0..1), clip?: Uint8Array W*H (0..255 limit), excl?: Uint8Array W*H (0..255 protect) }
    function generate(sp, rec) {
        const t0 = (root.performance || Date).now();
        const W = sp.W, H = sp.H, P = preset(rec.preset), G = P.g, k = Math.max(0, Math.min(1, (rec.laps == null ? P.def : rec.laps) / 100));
        const seed = (rec.seed | 0) || 1, geo = geometry(sp), F = fields(W, H, seed, geo.vertical), B = Buf(W, H);
        const kk = Math.pow(k, 0.85);
        // which sheet pixels may receive wear: part pixels x clip x (1 - exclusion)
        const owner = new Uint8Array(W * H);   // 1 + index of the part in sp.order (0 = not a part)
        sp.order.forEach((n, pi) => {
            const r = sp.parts[n]; if (!r || r.skip || !geo.parts[n]) return;
            for (let y = 0; y < r.h; y++) { const sy = (y + r.bb[1]) * W + r.bb[0], ry = y * r.w; for (let x = 0; x < r.w; x++) if (r.mask[ry + x] && !owner[sy + x]) owner[sy + x] = pi + 1; }
        });
        const inPart = i => owner[i] !== 0;
        const look2 = rec.look2 !== false;   // [REV-WEAR2] kill switch: window.SPB_REV_WEAR2_LOOK_OFF (the UI passes rec.look2)
        const feather = look2 ? edgeFeather(owner, W, H) : null;
        const Hs = sp.Hs, L = sp.L;

        // ---- 1) fields: dulled clear, road film / dust, mud cake, brake dust, wall scuff, heat haze (per pixel over every part)
        sp.order.forEach((n, pi) => {
            const r = sp.parts[n], o = geo.parts[n]; if (!r || !o) return;
            const vert = Math.abs(o.flow[1]) > Math.abs(o.flow[0]), s1 = vert ? F.sv1 : F.sh1, s2 = vert ? F.sv2 : F.sh2;
            const side = r.kind === 'side', top = r.kind === 'top', bump = r.kind === 'bumpF' || r.kind === 'bumpR';
            const sideSeed = o.side === 'L' ? 0.37 : 0;
            for (let y = 0; y < r.h; y++) {
                const sy = (y + r.bb[1]) * W + r.bb[0], ry = y * r.w;
                for (let x = 0; x < r.w; x++) {
                    const k2 = ry + x; if (!r.mask[k2]) continue;
                    const i = sy + x; if (owner[i] !== pi + 1) continue;
                    const u = r.U[k2], z = r.Z[k2], A = r.A[k2], X = u * L;
                    // domain warp (+-22 px): the shape fields are read at a displaced pixel, so no lattice grid survives in an edge
                    const ax = x + r.bb[0] + ((F.wx[i] - 128) * 0.17 | 0), ay = y + r.bb[1] + ((F.wy[i] - 128) * 0.17 | 0);
                    const j = (ay < 0 ? 0 : (ay >= H ? H - 1 : ay)) * W + (ax < 0 ? 0 : (ax >= W ? W - 1 : ax));
                    const g0 = h3(x + r.bb[0], y + r.bb[1], seed), n2 = F.n2[i] / 255, n8 = F.n8[j] / 255, n32 = F.n32[j] / 255, n128 = F.n128[i] / 255, st1 = s1[i] / 255, st2 = s2[i] / 255;   // streaks are NOT warped (they follow the airflow)
                    const fbm = n8 * 0.2 + n32 * 0.35 + n128 * 0.45;
                    // placement terms in car space
                    let low = 0, plume = 0, arch = 0, front = 0, hu = 0;
                    if (side) {
                        const Y = A - o.sill, zs = Math.max(0, Y) / Hs, zr = Math.max(0, zs + (fbm - 0.5) * 0.16 + (st2 - 0.5) * 0.05);   // ragged top line of the grime
                        low = Math.exp(-zr / (0.14 + 0.26 * kk));
                        for (let q = 0; q < o.arches.length; q++) {
                            const a = o.arches[q], dx = X - a.xc, rr = Math.hypot(dx, Y);
                            const dd = dx - 0.15 * a.r, Lp = a.r * (1.6 + 2.6 * kk), Hp = a.r * (0.45 + 0.9 * kk) * (1 + Math.max(0, dd) / Lp);
                            if (dd > -0.9 * a.r) { const pv = Math.exp(-Math.max(0, dd) / Lp) * Math.exp(-Math.max(0, Y) / Hp) * (dd < 0 ? Math.max(0, 1 + dd / (0.9 * a.r)) : 1); if (pv > plume) plume = pv; }
                            const band = Math.exp(-Math.pow((rr - a.r * 1.04) / (a.r * 0.16), 2)) * (dx > 0 ? 1.25 : 0.75) * (Y < a.r * 0.9 ? 1 : 0.4);
                            if (band > arch) arch = band;
                        }
                        front = Math.exp(-u / 0.12) * Math.exp(-zs / 0.35);
                    } else if (top) {
                        hu = (u - o.umin) / (o.umax - o.umin);
                        const rho = Math.max(0, Math.min(1, 1 - (A - Hs) / Math.max(1, sp.HWref)));
                        low = 0.12 + 0.25 * rho * rho + (o.isTrunk ? 0.35 * hu : 0);
                        front = o.isHood ? Math.exp(-hu / 0.2) : (o.isRoof ? 0.5 * Math.exp(-hu / 0.06) : 0);
                    } else if (bump) {
                        low = r.kind === 'bumpR' ? 0.75 : 0.45; front = r.kind === 'bumpF' ? 1 : 0; plume = r.kind === 'bumpR' ? 0.55 : 0;
                    } else { low = 0.15; }
                    // -- dulled clear (delta on CC, applied by the engine only where the car has clear)
                    let dull = G.dull * (14 + 58 * kk) * (0.5 + 0.5 * fbm) * (1 + 0.7 * low + 0.6 * front) + G.dull * kk * 10 * (n2 - 0.5);
                    // -- road film / dust: tint + dull rough spec, streaked along the airflow, grainy
                    // -- road film / dust: thin airflow streak lines over a mottled film, per-pixel grain; breaks up softly where it is light
                    let dust = G.dust * kk * (0.6 * low + 0.7 * plume) + G.spray * kk * 0.6 * plume;
                    if (dust > 0.01) {
                        const streaks = (0.4 + 0.6 * st2) * (0.55 + 0.45 * st1), mott = 0.5 + 0.8 * fbm;
                        let c = Math.min(0.88, dust * streaks * mott * (0.7 + 0.6 * g0) * 1.9);
                        c *= smooth(0.0, 0.5, fbm * 0.6 + dust * 0.7);
                        if (c > 0.03) {
                            const m = P.dust, sh = 0.84 + 0.32 * n8;
                            over(B, i, [m[0] * sh, m[1] * sh, m[2] * sh], c, MAT.dust.spec, Math.min(1, c * 1.2));
                            mark(B, x + r.bb[0], y + r.bb[1]);
                        }
                    }
                    // -- mud cake (dirt): crisp-edged clay masses on the lower panels and in the plumes, wet / dry two-tone + cracks inside
                    if (G.mud > 0 && (side || bump)) {
                        const reach = G.mud * (0.3 + 0.7 * kk) * (side ? Math.max(Math.pow(low, 1.3), plume) : plume * 0.9 + 0.15);
                        const v = reach * 1.4 + (fbm - 0.5) * 0.7 + (n8 - 0.5) * 0.25 + (st2 - 0.5) * 0.15 - 0.55;   // solid at the sill, ragged islands higher up
                        const c = Math.max(0, Math.min(1, v * 10));
                        if (c > 0.03) {
                            const dry = smooth(0.42, 0.72, n32 * 0.7 + n2 * 0.3), crack = (n2 > 0.88 && g0 > 0.45) ? 0.6 : 0;
                            const m0 = MAT.clay.col, m1 = MAT.claydry.col, t = Math.min(1, dry + crack), wet = 0.8 + 0.25 * n128;
                            const col = [m0[0] + (m1[0] - m0[0]) * t, m0[1] + (m1[1] - m0[1]) * t, m0[2] + (m1[2] - m0[2]) * t].map(cv => cv * wet * (0.9 + 0.2 * g0));
                            over(B, i, col, c, t > 0.5 ? MAT.claydry.spec : MAT.clay.spec, c); mark(B, x + r.bb[0], y + r.bb[1]);
                            dull += 30 * c;
                        }
                    }
                    // -- brake dust: fine dark grains ringing the arches, heavier on the trailing side
                    if (arch > 0.02 && G.brake > 0) {
                        const c = G.brake * (0.25 + 0.75 * kk) * arch * (0.45 + 0.55 * n8) * (g0 > 0.35 ? 1 : 0.45) * 0.9;
                        if (c > 0.03) { over(B, i, MAT.brake.col, Math.min(0.9, c), MAT.brake.spec, Math.min(1, c * 1.1)); mark(B, x + r.bb[0], y + r.bb[1]); }
                    }
                    // -- heat haze at the hood's rear edge (engine heat through the cowl)
                    if (G.heat > 0 && top && o.isHood) {
                        const ht = G.heat * kk * smooth(0.74, 0.98, hu + (n32 - 0.5) * 0.08) * (0.55 + 0.45 * n128);
                        if (ht > 0.01) { over(B, i, MAT.heat.col, Math.min(0.32, ht * 0.32), null, 0); dull += 70 * ht; mark(B, x + r.bb[0], y + r.bb[1]); }
                    }
                    B.dc[i] = Math.max(0, dull) * (rec.dullScale == null ? 1 : rec.dullScale);
                }
            }
        });

        // ---- 2) marks: candidates in a FIXED order per seed; each appears at its own lap threshold (more laps = a superset)
        const rnd = mulberry(seed * 9973 + 17);
        const parts = sp.order.map(n => ({ n, r: sp.parts[n], o: geo.parts[n] })).filter(p => p.r && p.o);
        const area = parts.reduce((s, p) => s + p.r.px, 0) || 1, cum = []; parts.reduce((s, p) => { s += p.r.px; cum.push(s); return s; }, 0);
        const pickPart = () => { const v = rnd() * area; for (let q = 0; q < cum.length; q++) if (v < cum[q]) return parts[q]; return parts[parts.length - 1]; };
        function pickPixel(p) {   // a random pixel of part p (rejection on its bbox) -> [x, y, k2] or null
            const r = p.r;
            for (let t = 0; t < 12; t++) { const x = (rnd() * r.w) | 0, y = (rnd() * r.h) | 0, k2 = y * r.w + x; if (r.mask[k2]) return [x + r.bb[0], y + r.bb[1], k2]; }
            return null;
        }
        function sideY(p, k2) { return p.r.A[k2] - p.o.sill; }
        // density of each mark class at a part pixel (0..1)
        function dens(cls, p, k2) {
            const r = p.r, o = p.o, u = r.U[k2];
            if (cls === 'chip') {
                if (r.kind === 'bumpF') return 1;
                if (r.kind === 'top') { const hu = (u - o.umin) / (o.umax - o.umin); return o.isHood ? Math.exp(-hu / 0.16) : (o.isRoof ? 0.35 * Math.exp(-hu / 0.05) : 0.03); }
                if (r.kind === 'side') {
                    const zs = Math.max(0, sideY(p, k2)) / Hs, X = u * L; let d = 0.75 * Math.exp(-u / 0.1) * Math.exp(-zs / 0.5) + 0.55 * Math.exp(-zs / 0.12);
                    if (o.arches.length > 1) { const a = o.arches[1], dx = a.xc - a.r - X; if (dx > 0) d += 0.8 * Math.exp(-dx / (a.r * 1.5)) * Math.exp(-zs / 0.3); }   // gravel thrown back at the leading edge of the rear arch
                    return Math.min(1, d);
                }
                return r.kind === 'bumpR' ? 0.1 : 0.05;
            }
            if (cls === 'pit') {   // [REV-WEAR2] sandblast on the leading edges (hood front, nose, roof lip, front of the side panels, front of the rocker)
                if (r.kind === 'bumpF') return 1;
                if (r.kind === 'top') { const hu = (u - o.umin) / (o.umax - o.umin); return o.isHood ? Math.exp(-hu / 0.085) : (o.isRoof ? 0.5 * Math.exp(-hu / 0.035) : 0); }
                if (r.kind === 'side') { const zs = Math.max(0, sideY(p, k2)) / Hs; return Math.min(1, 0.8 * Math.exp(-u / 0.05) * Math.exp(-zs / 0.6) + 0.25 * Math.exp(-zs / 0.05)); }
                return 0;
            }
            if (cls === 'bug') {
                if (r.kind === 'bumpF') return 1;
                if (r.kind === 'top') { const hu = (u - o.umin) / (o.umax - o.umin); return o.isHood ? Math.exp(-hu / 0.22) : (o.isRoof ? 0.6 * Math.exp(-hu / 0.07) : 0); }
                if (r.kind === 'side') { const zs = Math.max(0, sideY(p, k2)) / Hs; return 0.45 * Math.exp(-u / 0.07) * (zs > 0.2 ? 1 : 0.4); }
                if (r.kind === 'wing') return 0.08;
                return 0;
            }
            if (cls === 'drop') {   // mud / dust droplets: behind the arches + low on the sides, rear bumper
                if (r.kind === 'side') {
                    const Y = sideY(p, k2), zs = Math.max(0, Y) / Hs, X = u * L; let d = 0.5 * Math.exp(-zs / 0.38);
                    for (const a of o.arches) { const dx = X - a.xc; if (dx > -0.5 * a.r) d = Math.max(d, Math.exp(-Math.max(0, dx) / (a.r * 3)) * Math.exp(-Math.max(0, Y) / (a.r * 1.4))); }
                    return d;
                }
                if (r.kind === 'bumpR') return 0.8;
                if (r.kind === 'top') return 0.05;
                return 0.15;
            }
            return 0;
        }
        const cl = mulberry(seed * 131 + 9);
        function pickPartWith(r) { const v = r() * area; for (let q = 0; q < cum.length; q++) if (v < cum[q]) return parts[q]; return parts[parts.length - 1]; }
        function pickPixelWith(p, r) { const q = p.r; for (let t = 0; t < 12; t++) { const x = (r() * q.w) | 0, y = (r() * q.h) | 0, k2 = y * q.w + x; if (q.mask[k2]) return [x + q.bb[0], y + q.bb[1], k2]; } return null; }
        const exclAt = rec.excl ? (i => rec.excl[i]) : null;
        const maskOK = i => owner[i] !== 0;
        // chips
        if (G.chips > 0) {
            const N = Math.round(3600 * G.chips * Math.min(1.6, area / 1.8e6));
            for (let c = 0; c < N; c++) {
                const p = pickPart(), at = pickPixel(p), th = rnd(), sz = rnd(), mt = rnd(), dk = rnd(), rr = rnd();
                if (!at) continue;
                const d = dens('chip', p, at[2]); if (rr > d) continue;
                if (th > kk * (0.35 + 0.65 * G.chips)) continue;
                const rad = 0.6 + Math.pow(sz, 3.2) * 3.4;
                stampChip(B, maskOK, at[0], at[1], rad, rnd, mt < 0.4, 1, dk < (look2 ? 0.5 : 0.25), look2);
                if (look2 && rad > 1.1 && cl() < 0.5) {   // [REV-WEAR2] a stone hits in a spray: 1-3 smaller siblings around it (own random stream: the main sequence is untouched)
                    const ns = 1 + ((cl() * 3) | 0);
                    for (let q = 0; q < ns; q++) { const a = cl() * 6.2832, dd = rad * 1.8 + 3 + cl() * 16, r2 = Math.max(0.55, rad * (0.3 + cl() * 0.4)); stampChip(B, maskOK, Math.round(at[0] + Math.cos(a) * dd), Math.round(at[1] + Math.sin(a) * dd), r2, cl, cl() < 0.35, 1, cl() < 0.5, true); }
                }
            }
        }
        // [REV-WEAR2] leading-edge sandblast: a dense fine pitting on the hood's front edge, the nose, the roof lip and the front of the side panels (own random stream)
        if (look2 && G.pits > 0) {
            const NP = Math.round(5200 * G.pits * Math.min(1.6, area / 1.8e6)), pr = mulberry(seed * 977 + 5);
            for (let c = 0; c < NP; c++) {
                const p = pickPartWith(pr), at = pickPixelWith(p, pr), th = pr(), sz = pr(), mt = pr(), rr = pr();
                if (!at) continue;
                const d = dens('pit', p, at[2]); if (rr > d) continue;
                if (th > kk * (0.3 + 0.7 * G.pits)) continue;
                const rad = 0.45 + Math.pow(sz, 2.4) * 0.85, dark = mt < 0.7;
                stampChip(B, maskOK, at[0], at[1], rad, pr, mt > 0.93, 1, dark, true);
            }
        }
        // bugs
        if (G.bugs > 0) {
            const N = Math.round(6000 * G.bugs);
            for (let c = 0; c < N; c++) {
                const p = pickPart(), at = pickPixel(p), th = rnd(), sz = rnd(), ci = rnd(), rr = rnd(), tl = rnd();
                if (!at) continue;
                const d = dens('bug', p, at[2]); if (rr > d) continue;
                if (th > kk * G.bugs) continue;
                const col = BUGS[(ci * BUGS.length) | 0], rad = 1.2 + Math.pow(sz, 1.8) * 3.6, dir = p.o.flow;
                const tail = (dir[0] || dir[1]) ? 1.5 + tl * 3.5 : 0;
                stampBlob(B, maskOK, at[0], at[1], rad, rad * (0.7 + 0.3 * rnd()), dir[0] || dir[1] ? dir : [1, 0], col, [0, 120, 110], 0.92, rnd, tail);
                const ns = (rnd() * 4) | 0;   // satellite droplets
                for (let s = 0; s < ns; s++) { const a = rnd() * 6.28, dd = rad * (1.6 + rnd() * 2.5); stampBlob(B, maskOK, Math.round(at[0] + Math.cos(a) * dd), Math.round(at[1] + Math.sin(a) * dd), 0.7 + rnd() * 0.8, 0.6 + rnd() * 0.6, [1, 0], col, [0, 120, 110], 0.85, rnd, 0); }
            }
        }
        // spray droplets (mud on dirt, grime elsewhere): elongated along the throw (back and up), 1-6 px
        const dropG = G.mud > 0 ? G.mud : G.spray * 0.45;
        if (dropG > 0) {
            const N = Math.round((G.mud > 0 ? 14000 : 1800) * dropG);
            for (let c = 0; c < N; c++) {
                const p = pickPart(), at = pickPixel(p), th = rnd(), sz = rnd(), rr = rnd(), el = rnd();
                if (!at) continue;
                const d = dens('drop', p, at[2]); if (rr > d) continue;
                if (th > kk * dropG) continue;
                const m = G.mud > 0 ? (rnd() < 0.6 ? MAT.clay : MAT.claydry) : MAT.dust, rad = 0.6 + Math.pow(sz, 2.6) * (G.mud > 0 ? 5 : 2);
                const dir = p.o.flow[0] || p.o.flow[1] ? [p.o.flow[0] * 0.8 - p.o.flow[1] * 0.3, p.o.flow[1] * 0.8 + p.o.flow[0] * 0.3] : [1, 0];
                stampBlob(B, maskOK, at[0], at[1], rad * (1 + el * 1.4), rad, dir, m.col.map(v => v * (0.85 + 0.3 * rnd())), m.spec, G.mud > 0 ? 0.95 : 0.6, rnd, G.mud > 0 && el > 0.7 ? 1.2 : 0);
            }
        }
        // rubber: tyre donuts (arcs) + door-rub streaks at door height on both sides (between the arches)
        if (G.rubber > 0) {
            parts.filter(p => p.r.kind === 'side' && p.o.arches.length > 1).forEach(p => {
                const r = p.r, o = p.o, a0 = o.arches[0], a1 = o.arches[1], N = Math.round(14 * G.rubber);
                const loc = mulberry(seed * 31 + (o.side === 'L' ? 7 : 3));
                for (let c = 0; c < N; c++) {
                    const th = loc(), kind = loc(), uX = a0.xc + a0.r * 1.1 + loc() * (a1.xc - a1.r * 1.1 - a0.xc - a0.r * 1.1), zY = o.sill + Hs * (0.22 + loc() * 0.38);
                    const ln = loc(), thick = 18 + loc() * 36, rad = 140 + loc() * 120, span = 0.8 + loc() * 1.6, ang = loc() * 6.28, al = 0.45 + loc() * 0.4;   // real scale: 1 px ~ 2.8 mm (tyre ~ 107 px wide)
                    if (th > kk * G.rubber * (o.side === 'R' ? 1 : 0.8)) continue;
                    // find the sheet pixel at (uX, zY) by scanning the part (coarse) -> nearest
                    const at = locate(r, uX / L, zY, sp); if (!at) continue;
                    if (kind < 0.45) rubberArc(B, maskOK, at[0], at[1], rad, thick, ang, span, al, F, seed);
                    else rubberStreak(B, maskOK, at[0], at[1], p.o.flow, 160 + ln * 360, thick * 0.45, al, F, loc, MAT.rubber, 3, (loc() - 0.5) * 0.12, 0.8);
                }
            });
        }
        // wall contact (oval, RIGHT side): a few contact events along the right rear quarter / door at wall height; each = white wall-paint
        // transfer smears + bundles of 1 px scratches through to primer + a black rubber line. Crisp stamps (2026-10-10 v2: the per-pixel band read as a smudge).
        if (G.wall > 0) {
            parts.filter(p => p.r.kind === 'side' && p.o.side === 'R').forEach(p => {
                const r = p.r, o = p.o, loc = mulberry(seed * 53 + 5), NE = 6;
                for (let e = 0; e < NE; e++) {
                    const th = loc(), uu = 0.34 + loc() * 0.6, zz = 0.34 + loc() * 0.22, nl = 8 + ((loc() * 14) | 0), span = 120 + loc() * 260, tl = (loc() - 0.5) * 0.06;
                    if (th > kk * G.wall * 1.1) continue;
                    const at = locate(r, uu, o.sill + zz * Hs, sp); if (!at) continue;
                    rubberStreak(B, maskOK, at[0], at[1], o.flow, span, 10 + loc() * 16, 0.8, F, loc, MAT.wall, 1.2, tl, 0.9);
                    for (let q = 0; q < nl; q++) {
                        const ox = (loc() - 0.5) * span * 0.8, oy = (loc() - 0.5) * 34, len = 30 + loc() * span * 0.7;
                        rubberStreak(B, maskOK, Math.round(at[0] + ox * o.flow[0] - oy * o.flow[1]), Math.round(at[1] + ox * o.flow[1] + oy * o.flow[0]), o.flow, len, 0.6 + loc() * 0.7, 0.95, F, loc, loc() < 0.7 ? MAT.primer : MAT.wall, 0.4, tl + (loc() - 0.5) * 0.02);
                    }
                    if (loc() < 0.7) rubberStreak(B, maskOK, at[0], Math.round(at[1] + (loc() - 0.5) * 30), o.flow, span * 0.6, 6 + loc() * 8, 0.7, F, loc, MAT.rubber, 1, tl, 0.8);
                }
            });
        }
        // [REV-WEAR2 2026-10-10] door-bang scuffs at bumper height: on BOTH sides, between the arches (where another car's bumper lands). Each event = a paint-transfer smear
        // (white / red / black rubber) laid along the airflow, 6-14 fine parallel scratch lines through to primer that fan out of it, and a scuffed-clear halo.
        if (look2 && G.scuff > 0) {
            const XF = [[205, 205, 200], [150, 48, 44], [30, 30, 32], [190, 160, 56], [66, 88, 128]];   // muted: another car's paint, scuffed
            parts.filter(p => p.r.kind === 'side' && p.o.arches.length > 1).forEach(p => {
                const r = p.r, o = p.o, a0 = o.arches[0], a1 = o.arches[1], loc = mulberry(seed * 61 + (o.side === 'L' ? 11 : 4)), NE = Math.max(1, Math.round(5 * G.scuff));
                for (let e = 0; e < NE; e++) {
                    const th = loc(), uu = (a0.xc + a0.r * 1.15 + loc() * (a1.xc - a1.r * 1.15 - a0.xc - a0.r * 1.15)) / L, zz = 0.2 + loc() * 0.22, nl = 6 + ((loc() * 9) | 0), span = 50 + loc() * 140, tl = (loc() - 0.5) * 0.18, tcol = XF[(loc() * XF.length) | 0];
                    if (th > kk * G.scuff * 1.2 * (o.side === 'R' && G.wall > 0 ? 0.6 : 1)) continue;
                    const at = locate(r, uu, o.sill + zz * Hs, sp); if (!at) continue;
                    const mat = { col: tcol, spec: MAT.wall.spec };
                    rubberStreak(B, maskOK, at[0], at[1], o.flow, span, 4 + loc() * 7, 0.55, F, loc, mat, 1.4, tl, 0.85);
                    for (let q = 0; q < nl; q++) {
                        const ox = (loc() - 0.5) * span * 0.9, oy = (loc() - 0.5) * 26, len = 24 + loc() * span * 0.8;
                        rubberStreak(B, maskOK, Math.round(at[0] + ox * o.flow[0] - oy * o.flow[1]), Math.round(at[1] + ox * o.flow[1] + oy * o.flow[0]), o.flow, len, 0.55 + loc() * 0.6, 0.92, F, loc, loc() < 0.75 ? MAT.primer : { col: tcol, spec: MAT.wall.spec }, 0.35, tl + (loc() - 0.5) * 0.05);
                    }
                }
            });
        }
        // speed tape across the nose (endurance)
        if (G.tape > 0 && kk > 0.15) {
            parts.filter(p => p.r.kind === 'bumpF').forEach(p => tapeStrips(B, maskOK, p.r, rnd, kk));
        }

        // ---- 3) resolve: val = premul / cov, opacity, clip, exclusion; CC snapped out of 1..15
        const op = rec.opacity == null ? 1 : Math.max(0, Math.min(1, rec.opacity));
        const N = W * H, pv = new Uint8Array(N * 3), pc = new Uint8Array(N), sv = new Uint8Array(N * 3), sc = new Uint8Array(N), dc = new Uint8Array(N);
        let bx0 = W, by0 = H, bx1 = -1, by1 = -1, nP = 0, nS = 0;
        const clip = rec.clip || null;
        for (let i = 0; i < N; i++) {
            if (!owner[i]) continue;
            let lim = op; if (clip) lim *= clip[i] / 255; if (exclAt) lim *= 1 - exclAt(i) / 255;
            if (feather) lim *= feather[i] / 255;   // [REV-WEAR2] 3 px feather at part edges / template holes
            if (lim <= 0) continue;
            const pa = B.pa[i], sa = B.sa[i], d = B.dc[i] * lim, o3 = i * 3;
            let any = false;
            if (pa > 0.002) { const iv = 1 / pa; pv[o3] = B.pp[o3] * iv; pv[o3 + 1] = B.pp[o3 + 1] * iv; pv[o3 + 2] = B.pp[o3 + 2] * iv; pc[i] = Math.min(255, Math.round(pa * lim * 255)); if (pc[i]) { any = true; nP++; } }
            if (sa > 0.002) {
                const iv = 1 / sa; sv[o3] = B.sp[o3] * iv; sv[o3 + 1] = B.sp[o3 + 1] * iv; sv[o3 + 2] = snapCC(Math.round(B.sp[o3 + 2] * iv));
                sc[i] = Math.min(255, Math.round(sa * lim * 255)); if (sc[i]) { any = true; nS++; }
            }
            if (d >= 0.5) { dc[i] = Math.min(255, Math.round(d)); any = true; }
            if (any) { const x = i % W, y = (i / W) | 0; if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
        }
        const ms = Math.round(((root.performance || Date).now()) - t0);
        return { v: 1, W, H, pv, pc, sv, sc, dc, bbox: bx1 < 0 ? null : [bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1], ms, nP, nS, geo: describeGeo(geo, sp) };
    }

    // nearest sheet pixel of side part r at car position (u, A) (coarse search, stride 3)
    function locate(r, u, A, sp) {
        let best = null, bd = 1e18;
        for (let y = 0; y < r.h; y += 3) for (let x = 0; x < r.w; x += 3) {
            const k = y * r.w + x; if (!r.mask[k]) continue;
            const d = Math.pow((r.U[k] - u) * sp.L, 2) + Math.pow(r.A[k] - A, 2);
            if (d < bd) { bd = d; best = [x + r.bb[0], y + r.bb[1]]; }
        }
        return bd < 40 * 40 ? best : null;
    }
    function rubberArc(B, mask, cx, cy, R, th, a0, span, al, F, seed) {
        const W = B.W, H = B.H, Rb = Math.ceil(R + th) + 2;
        for (let dy = -Rb; dy <= Rb; dy++) for (let dx = -Rb; dx <= Rb; dx++) {
            const px = cx + dx, py = cy + dy; if (px < 0 || py < 0 || px >= W || py >= H) continue;
            const i = py * W + px; if (!mask(i)) continue;
            let ang = Math.atan2(dy, dx) - a0; while (ang < 0) ang += 6.2832; if (ang > span) continue;
            const rr = Math.hypot(dx, dy), d = Math.abs(rr - R) / th, prof = d >= 1 ? 0 : (1 - d * d) * (1 - d * d);
            const ends = Math.min(1, ang / 0.35, (span - ang) / 0.6), grain = 0.55 + 0.45 * (F.n2[i] / 255), tread = 0.3 + 0.7 * h3(Math.round(rr), 7, seed);
            const c = Math.min(0.9, prof * ends * grain * tread * al * 1.5); if (c <= 0.03) continue;
            over(B, i, MAT.rubber.col, c, MAT.rubber.spec, c >= 0.5 ? 1 : 0); mark(B, px, py);
        }
    }
    function rubberStreak(B, mask, cx, cy, flow, len, th, al, F, rnd, mat, wamp, tilt, rough) {
        mat = mat || MAT.rubber; tilt = tilt || 0; rough = rough || 0; const lseed = (rnd() * 1e6) | 0;
        const W = B.W, H = B.H, c0 = Math.cos(tilt), s0 = Math.sin(tilt), ux = (flow[0] || 1) * c0 - (flow[1] || 0) * s0, uy = (flow[0] || 1) * s0 + (flow[1] || 0) * c0, wob = rnd() * 6.28, wa = wamp == null ? 1 + rnd() * 3 : wamp, ph = rnd();
        const ext = Math.ceil(len / 2 + th + 4);
        for (let dy = -ext; dy <= ext; dy++) for (let dx = -ext; dx <= ext; dx++) {
            const s = dx * ux + dy * uy; if (Math.abs(s) > len / 2) continue;
            const t = -dx * uy + dy * ux - wa * Math.sin(s / 40 + wob); if (Math.abs(t) > th + 1) continue;
            const px = cx + dx, py = cy + dy; if (px < 0 || py < 0 || px >= W || py >= H) continue;
            const i = py * W + px; if (!mask(i)) continue;
            const q = (s + len / 2) / len, fade = Math.min(1, q / 0.15, (1 - q) / 0.35), prof = Math.max(0, Math.min(1, th - Math.abs(t) + 0.5));
            const lines = rough ? (1 - rough) + rough * Math.pow(h3(Math.round(t * 1.3), 3, lseed), 1.5) * 1.6 : 1;   // parallel scrape lines of random strength
            const streak = 0.45 + 0.55 * (F.sh1[i] / 255), c = Math.min(0.92, prof * fade * streak * lines * al * (0.7 + 0.3 * Math.sin(q * 9 + ph * 6)) * 1.3); if (c <= 0.03) continue;
            over(B, i, mat.col, c, mat.spec, mat.spec && mat.spec[2] < 16 ? (c >= 0.5 ? 1 : 0) : c); mark(B, px, py);
        }
    }
    function tapeStrips(B, mask, r, rnd, kk) {
        // the front bumper's own mirror line gives the car's lateral direction on the sheet (r.n, set by fade-space); strips run across it
        const n = r.n || [1, 0], W = B.W; let cx = 0, cy = 0, c = 0;
        for (let y = 0; y < r.h; y += 2) for (let x = 0; x < r.w; x += 2) if (r.mask[y * r.w + x]) { cx += x; cy += y; c++; }
        if (!c) return; cx = cx / c + r.bb[0]; cy = cy / c + r.bb[1];
        let e0 = 0, e1 = 0;   // extents along the lateral and the vertical (n-perp) axes
        for (let y = 0; y < r.h; y += 2) for (let x = 0; x < r.w; x += 2) if (r.mask[y * r.w + x]) { const dx = x + r.bb[0] - cx, dy = y + r.bb[1] - cy; e0 = Math.max(e0, Math.abs(dx * n[0] + dy * n[1])); e1 = Math.max(e1, Math.abs(-dx * n[1] + dy * n[0])); }
        const strips = kk > 0.6 ? [-0.18, 0.08] : [-0.18];
        strips.forEach((off, si) => {
            const hw = e0 * (0.22 + 0.08 * si), hh = 9 + si * 2, oy = off * e1, j1 = rnd() * 6.28, j2 = rnd() * 6.28;
            const R = Math.ceil(Math.hypot(hw, hh)) + 4;
            for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
                const s = dx * n[0] + dy * n[1], t = -dx * n[1] + dy * n[0];
                const px = Math.round(cx + dx - n[1] * oy), py = Math.round(cy + dy + n[0] * oy); if (px < 0 || py < 0 || px >= W || py >= B.H) continue;
                const torn = 2.5 * Math.sin(t * 1.7 + j1) + 1.5 * Math.sin(t * 3.1 + j2);   // torn ends
                if (Math.abs(t) > hh || Math.abs(s) > hw + torn) continue;
                const i = py * W + px; if (!mask(i)) continue;
                const edge = Math.min(1, hh - Math.abs(t) + 0.5), sheen = 0.93 + 0.05 * Math.sin(s * 0.021 + j2) + 0.03 * Math.sin(s * 0.11 + t * 0.05), crease = (Math.abs(t - hh * 0.35 * Math.sin(j1)) < 0.6 && (s * 0.013 + j2) % 1 < 0.5) ? 0.86 : 1;
                const col = MAT.tape.col.map(v => v * sheen * crease);
                over(B, i, col, Math.max(0, edge), MAT.tape.spec, edge >= 0.5 ? 1 : 0); mark(B, px, py);
            }
        });
    }
    function describeGeo(geo, sp) {
        const o = {};
        Object.values(geo.parts).forEach(p => { if (p.kind === 'side') o[p.name] = { measured: p.measured, arches: p.arches.map(a => [+(a.xc / sp.L).toFixed(3), +(a.r / sp.L).toFixed(3)]) }; });
        return o;
    }

    root.SpbRevWear = Object.assign(root.SpbRevWear || {}, {
        version: VER, off, PRESETS, MAT, preset, lapsText, generate, geometry, snapCC, _internal: { lattice, fields, sideFrame, mulberry, h3 }
    });
})(typeof window !== 'undefined' ? window : globalThis);
