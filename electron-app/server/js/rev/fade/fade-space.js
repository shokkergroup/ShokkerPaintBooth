/* [SPB-REV-FADE 2026-10-10] Car-Space Fade - core: the car-space coordinate of every pixel of the flat sheet + the fade maths.
 *
 * An iRacing paint is ONE flat UV sheet: the car cut into islands (two side panels, hood, roof, trunk, bumpers ...), each laid out
 * and turned its own way (the nose is on the LEFT for both side panels and on the RIGHT for hood / roof / trunk of the owner's ARCA).
 * A gradient on the sheet therefore runs a different way on every island. This module gives every pixel a CAR-SPACE position instead:
 *   u  0 nose ... 1 tail                      (length)
 *   z  0 sill ... 1 roof crown                 (height; the top islands sit in the top 10 %: z = ZSH + (1-ZSH)(1-rho^2))
 *   a  arc length from the sill, up the side, over the shoulder to the centre line (px of the side panel; "a" is what Centre -> Out uses)
 * from the part registration SpbRevSym already builds (left <-> right side maps, each centre island's own mirror line) and the car map's
 * front / up flags. No sym-core.js change is needed: only SpbRevSym.cur() and SpbRevSym.mapPt() are used.
 *
 *  - side panels: the RIGHT panel (pair.a) gets u / z from its own extents along its front / up axes; the LEFT panel is mapped into
 *    the right panel's frame through the registered left->right map, so both sides match at the same car position by construction.
 *  - hood / roof / trunk (the "top row"): u = linear in the sheet position along their common front axis over the union of the islands,
 *    glass gaps between them included (the template's top view keeps them in place), rescaled into [U0, U1]; rho = |lateral| / half width of
 *    the island, the lateral distance from the island's own mirror line (the line Car Stripe follows).
 *  - bumpers: u at the nose / tail (+ a small wrap-around by rho); spoiler / wing: tail, high.
 * A fade direction is a linear functional of (u, z, a): nose->tail = u, bottom->top = z, centre->out = -a, custom = two clicks in (u, a).
 *
 * KILL SWITCH: window.SPB_REV_FADE_OFF = true or localStorage SPB_REV_FADE_OFF = '1' -> SpbRevFade.ready() is false, no UI.
 */
(function (root) {
    'use strict';
    const VER = 'fade1.0';
    const doc = root.document;

    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_FADE_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_FADE_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_FADE_OFF); }
    }

    // ---------------------------------------------------------------- constants
    const FRONT = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };
    const K = { U0: 0.03, U1: 0.97, ZSH: 0.9, BUMP_U: 0.03, BUMP_Z: 0.25, PAD: 10, DIL: 8, STEP: 2 };
    const TOP_RE = /^(hood|roof|trunk|bed|cab|deck)$/i;
    const FRONT_RE = /front bumper/i, REAR_RE = /(rear bumper|tailgate)/i, WING_RE = /(spoiler|top wing|tank)/i;
    const LUT_N = 1024;

    // ---------------------------------------------------------------- geometry helpers
    function bboxOf(mask, W, H) {
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        for (let y = 0; y < H; y++) {
            const r = y * W;
            for (let x = 0; x < W; x++) if (mask[r + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        }
        return x1 >= 0 ? [x0, y0, x1, y1] : null;
    }
    function projRange(bb, f) { // min / max of x*f0 + y*f1 over a bbox (axis-aligned f)
        const c = [[bb[0], bb[1]], [bb[2], bb[1]], [bb[0], bb[3]], [bb[2], bb[3]]].map(p => p[0] * f[0] + p[1] * f[1]);
        return [Math.min.apply(null, c), Math.max.apply(null, c)];
    }
    function partFlags(name) {
        try { const b = root.SpbProCar.map().boxes[name]; return { front: (b && b.front) || null, up: (b && b.up) || null }; } catch (e) { return { front: null, up: null }; }
    }
    function fullMask(name, W, H) {
        try { const r = root.SpbProCar.maskFor(name); if (r && r.mask && r.mask.length === W * H && !r.empty) return r.mask; } catch (e) {}
        return null;
    }
    function axisNormal(M) { // unit normal of a centre island's mirror line = null vector of (A + I) of its reflection (same as Car Stripe's axisOf)
        const A = M.A, a = A[0] + 1, b = A[1], c = A[3], d = A[4] + 1;
        let x = -b, y = a; const x2 = d, y2 = -c;
        if (x2 * x2 + y2 * y2 > x * x + y * y) { x = x2; y = y2; }
        const n = Math.hypot(x, y) || 1;
        return [x / n, y / n];
    }
    function dilate(m, w, h, r) { // separable box max of a 0/1 crop
        const tmp = new Uint8Array(w * h), out = new Uint8Array(w * h);
        for (let y = 0; y < h; y++) {
            const o = y * w; let last = -1e9;
            for (let x = 0; x < w; x++) if (m[o + x]) last = x, tmp[o + x] = 1; else tmp[o + x] = (x - last <= r) ? 1 : 0;
            last = 1e9;
            for (let x = w - 1; x >= 0; x--) { if (m[o + x]) last = x; if (last - x <= r) tmp[o + x] = 1; }
        }
        for (let x = 0; x < w; x++) {
            let last = -1e9;
            for (let y = 0; y < h; y++) { const i = y * w + x; if (tmp[i]) last = y, out[i] = 1; else out[i] = (y - last <= r) ? 1 : 0; }
            last = 1e9;
            for (let y = h - 1; y >= 0; y--) { const i = y * w + x; if (tmp[i]) last = y; if (last - y <= r) out[i] = 1; }
        }
        return out;
    }
    // bilinear fill of a full-resolution crop from a coarse grid sampled every STEP px (grid node (i,j) = pixel (x0 + STEP i, y0 + STEP j))
    function upFill(cs, cw, ch, w, h, out) {
        const S = K.STEP;
        for (let y = 0; y < h; y++) {
            const fy = y / S, j = Math.min(ch - 2, Math.floor(fy)), ty = fy - j, r0 = j * cw, r1 = r0 + cw, o = y * w;
            for (let x = 0; x < w; x++) {
                const fx = x / S, i = Math.min(cw - 2, Math.floor(fx)), tx = fx - i;
                out[o + x] = (cs[r0 + i] * (1 - tx) + cs[r0 + i + 1] * tx) * (1 - ty) + (cs[r1 + i] * (1 - tx) + cs[r1 + i + 1] * tx) * ty;
            }
        }
    }

    // ---------------------------------------------------------------- the space
    let CUR = null, BUSY = null;
    function build(force) {
        if (off()) return Promise.resolve(null);
        if (!root.SpbRevSym) return Promise.resolve(null);
        if (BUSY) return BUSY;
        BUSY = Promise.resolve(root.SpbRevSym.build(!!force && false)).then(C => {
            if (!C) return null;
            if (!force && CUR && CUR.key === C.key && CUR.syncVer === (root.SpbRevSym.version || '')) return CUR;
            CUR = compute(C); return CUR;
        }).then(r => { BUSY = null; return r; }, e => { BUSY = null; throw e; });
        return BUSY;
    }

    function compute(C) {
        const t0 = (root.performance || Date).now();
        const W = C.W, H = C.H, sym = root.SpbRevSym, sp = { ver: VER, key: C.key, syncVer: sym.version || '', W, H, parts: {}, order: [], warn: [], info: {} };
        const mapPt = sym.mapPt;
        const have = new Set(C.names || []);
        const selfOf = n => { const m = C.maps[n + '>' + n]; return m && m.M ? m.M : null; };

        // ---- 1) the reference side panel (frame of the whole car)
        const pairs = C.reg.pairs || [];
        const sidePair = pairs.find(p => /side/i.test(p.a) || /side/i.test(p.b)) || null;
        let ref = null;
        if (sidePair) {
            const a = sidePair.a, ma = C.masks[a], bb = ma && bboxOf(ma, W, H);
            if (bb) {
                const fl = partFlags(a);
                if (!fl.front || !fl.up) sp.warn.push('car map has no nose / roof-line flags for ' + a + ': assumed nose left, roof up');
                const f = FRONT[fl.front] || FRONT.left, up = FRONT[fl.up] || FRONT.top;
                const pf = projRange(bb, f), pu = projRange(bb, up);
                ref = { part: a, partner: sidePair.b, f, up, pf, pu, L: pf[1] - pf[0], Hs: pu[1] - pu[0] };
            }
        }
        const Lsheet = ref ? ref.L : 1800, Hs = ref ? ref.Hs : 450;

        // ---- 2) top row: common front axis over hood / roof / trunk (glass gaps included)
        const topNames = (C.reg.selfs || []).map(s => s.part).filter(n => TOP_RE.test(n) && have.has(n));
        const topInfo = {};
        let row = null;
        if (topNames.length) {
            const fls = topNames.map(n => partFlags(n).front);
            const same = fls.every(f => f && f === fls[0]);
            if (same) {
                const f = FRONT[fls[0]];
                let mn = 1e9, mx = -1e9;
                topNames.forEach(n => { const bb = bboxOf(C.masks[n], W, H); if (!bb) return; const r = projRange(bb, f); mn = Math.min(mn, r[0]); mx = Math.max(mx, r[1]); });
                row = { mode: 'axis', f, mn, mx };
            } else { // mixed / missing flags: chain the islands one after the other (hood, roof, trunk) by their own length - no glass gap known
                const ord = ['hood', 'cab', 'roof', 'deck', 'trunk', 'bed'].filter(n => topNames.indexOf(n) >= 0);
                let off0 = 0, tot = 0; const items = {};
                ord.forEach(n => { const bb = bboxOf(C.masks[n], W, H); if (!bb) return; const f = FRONT[partFlags(n).front] || FRONT.right, r = projRange(bb, f); items[n] = { f, mn: r[0], mx: r[1], off: tot, len: r[1] - r[0] }; tot += r[1] - r[0]; });
                row = { mode: 'chain', items, tot };
                sp.warn.push('hood / roof / trunk have different front flags: chained end to end (no windshield / rear-window gap)');
            }
        }
        const uRow = (n, x, y) => {
            if (!row) return 0.5;
            if (row.mode === 'axis') return (row.mx - (x * row.f[0] + y * row.f[1])) / Math.max(1, row.mx - row.mn);
            const it = row.items[n]; if (!it) return 0.5;
            return (it.off + (it.mx - (x * it.f[0] + y * it.f[1]))) / Math.max(1, row.tot);
        };

        // ---- 3) every registered part: classify, bbox, mask, lateral field
        const names = (C.names || []).slice();
        const recs = [];
        names.forEach(n => {
            const m = fullMask(n, W, H); if (!m) return;
            const bb0 = bboxOf(m, W, H); if (!bb0) return;
            let kind = null;
            if (sidePair && (n === sidePair.a || n === sidePair.b)) kind = 'side';
            else if (!selfOf(n)) kind = null;
            else if (TOP_RE.test(n)) kind = 'top';
            else if (FRONT_RE.test(n)) kind = 'bumpF';
            else if (REAR_RE.test(n)) kind = 'bumpR';
            else if (WING_RE.test(n)) kind = 'wing';
            if (!kind) return;
            if (kind === 'side' && !ref) return;
            const x0 = Math.max(0, bb0[0] - K.PAD), y0 = Math.max(0, bb0[1] - K.PAD), x1 = Math.min(W - 1, bb0[2] + K.PAD), y1 = Math.min(H - 1, bb0[3] + K.PAD);
            const w = x1 - x0 + 1, h = y1 - y0 + 1, crop = new Uint8Array(w * h);
            for (let y = 0; y < h; y++) { const s = (y + y0) * W + x0, o = y * w; for (let x = 0; x < w; x++) crop[o + x] = m[s + x] ? 1 : 0; }
            recs.push({ name: n, kind, bb: [x0, y0, x1, y1], w, h, mask: crop, px: 0 });
        });
        recs.forEach(r => { let c = 0; for (let i = 0; i < r.mask.length; i++) c += r.mask[i]; r.px = c; });

        // coarse lateral field of the centre islands -> half widths
        const S = K.STEP;
        recs.forEach(r => {
            if (r.kind === 'side') return;
            const M = selfOf(r.name), n = axisNormal(M), cw = Math.ceil(r.w / S) + 1, ch = Math.ceil(r.h / S) + 1, lc = new Float32Array(cw * ch);
            for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
                const x = r.bb[0] + Math.min(S * i, r.w - 1 + 0), y = r.bb[1] + Math.min(S * j, r.h - 1 + 0), q = mapPt(M, x, y);
                lc[j * cw + i] = ((x - q[0]) * n[0] + (y - q[1]) * n[1]) / 2;
            }
            r.cw = cw; r.ch = ch; r.lc = lc; r.n = n;
            // half width = 98th percentile of |lateral| over the part's own pixels (coarse)
            const vals = []; for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) { const px = Math.min(S * i, r.w - 1), py = Math.min(S * j, r.h - 1); if (r.mask[py * r.w + px]) vals.push(Math.abs(lc[j * cw + i])); }
            vals.sort((p, q) => p - q);
            r.hw = vals.length ? Math.max(8, vals[Math.min(vals.length - 1, Math.floor(vals.length * 0.98))]) : 100;
        });
        const hws = recs.filter(r => r.kind === 'top').map(r => r.hw).sort((p, q) => p - q);
        const HWref = hws.length ? hws[hws.length >> 1] : Hs * 0.8;
        sp.L = Lsheet; sp.Hs = Hs; sp.HWref = HWref; sp.AMAX = Hs + HWref;

        // ---- 4) fields per part (u, z, a), full resolution over the padded bbox; coarse -> bilinear
        const mk = n => new Float32Array(n);
        recs.forEach(r => {
            const N = r.w * r.h; r.U = mk(N); r.Z = mk(N); r.A = mk(N);
            if (r.kind === 'side') {
                const isRef = r.name === ref.part, mp = isRef ? null : (C.maps[r.name + '>' + ref.part] && C.maps[r.name + '>' + ref.part].M);
                if (!isRef && !mp) { r.skip = true; return; }
                const cw = Math.ceil(r.w / S) + 1, ch = Math.ceil(r.h / S) + 1, cu = mk(cw * ch), cz = mk(cw * ch);
                for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
                    let x = r.bb[0] + Math.min(S * i, r.w - 1), y = r.bb[1] + Math.min(S * j, r.h - 1);
                    if (mp) { const q = mapPt(mp, x, y); x = q[0]; y = q[1]; }
                    cu[j * cw + i] = (ref.pf[1] - (x * ref.f[0] + y * ref.f[1])) / ref.L;
                    cz[j * cw + i] = ((x * ref.up[0] + y * ref.up[1]) - ref.pu[0]) / ref.Hs;
                }
                upFill(cu, cw, ch, r.w, r.h, r.U); upFill(cz, cw, ch, r.w, r.h, r.Z); // Z holds the side's own 0..1 height for now
                for (let k = 0; k < N; k++) { const zs = r.Z[k]; r.A[k] = zs * Hs; r.Z[k] = K.ZSH * zs; }
                return;
            }
            const rho = mk(N); upFill(r.lc, r.cw, r.ch, r.w, r.h, rho);
            for (let k = 0; k < N; k++) { const v = Math.abs(rho[k]) / r.hw; rho[k] = v > 1 ? 1 : v; }
            for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) {
                const k = y * r.w + x, p = rho[k], px = x + r.bb[0], py = y + r.bb[1];
                if (r.kind === 'top') {
                    r.U[k] = K.U0 + (K.U1 - K.U0) * uRow(r.name, px, py);
                    r.Z[k] = K.ZSH + (1 - K.ZSH) * (1 - p * p);
                    r.A[k] = Hs + (1 - p) * HWref;
                } else if (r.kind === 'bumpF') {
                    r.U[k] = K.BUMP_U * p; r.Z[k] = K.ZSH * K.BUMP_Z; r.A[k] = Hs * 0.5 + (1 - p) * (Hs * 0.5 + HWref);
                } else if (r.kind === 'bumpR') {
                    r.U[k] = 1 - K.BUMP_U * p; r.Z[k] = K.ZSH * K.BUMP_Z; r.A[k] = Hs * 0.5 + (1 - p) * (Hs * 0.5 + HWref);
                } else { // wing
                    r.U[k] = 0.965; r.Z[k] = 1; r.A[k] = Hs + (1 - p) * HWref;
                }
            }
            delete r.lc;
        });
        recs.forEach(r => { r.dil = r.skip ? null : dilate(r.mask, r.w, r.h, K.DIL); sp.parts[r.name] = r; sp.order.push(r.name); });
        sp.order = sp.order.filter(n => !sp.parts[n].skip);
        sp.info = { ref: ref ? ref.part : null, sidePair: sidePair ? [sidePair.a, sidePair.b] : null, topRow: row ? row.mode : null, tops: topNames, HWref: Math.round(HWref), L: Math.round(Lsheet), Hs: Math.round(Hs), warn: sp.warn };
        sp.ms = Math.round(((root.performance || Date).now()) - t0);
        // point lookup: which part holds sheet pixel (x, y) and its car-space position
        sp.at = function (x, y) {
            x = Math.round(x); y = Math.round(y);
            for (let i = 0; i < sp.order.length; i++) {
                const r = sp.parts[sp.order[i]];
                if (x < r.bb[0] || x > r.bb[2] || y < r.bb[1] || y > r.bb[3]) continue;
                const k = (y - r.bb[1]) * r.w + (x - r.bb[0]);
                if (r.mask[k]) return { part: r.name, u: r.U[k], z: r.Z[k], a: r.A[k] };
            }
            return null;
        };
        return sp;
    }

    // ---------------------------------------------------------------- fade direction -> linear functional of (u, z, a)
    // dir: { kind: 'nose' | 'height' | 'out' | 'custom', rev: bool, span: 'car' | 'sel', custom: {u1,a1,u2,a2} }
    // q = c0 + cu*u + cz*z + ca*a ; t = (q - qmin) / (qmax - qmin)  (custom: t = q directly, already 0 at the first click and 1 at the second)
    function prepare(sp, dir, sel) {
        const d = dir || { kind: 'nose' };
        const o = { c0: 0, cu: 0, cz: 0, ca: 0, qmin: 0, qmax: 1, rev: !!d.rev, kind: d.kind, custom: false };
        if (d.kind === 'nose') o.cu = 1;
        else if (d.kind === 'height') o.cz = 1;
        else if (d.kind === 'out') o.ca = -1;
        else if (d.kind === 'custom' && d.custom) {
            const c = d.custom, dx = (c.u2 - c.u1) * sp.L, dy = (c.a2 - c.a1), dd = dx * dx + dy * dy;
            if (dd > 1e-6) { o.custom = true; o.cu = dx * sp.L / dd; o.ca = dy / dd; o.c0 = -(dx * c.u1 * sp.L + dy * c.a1) / dd; }
            else o.cu = 1;
        } else o.cu = 1;
        if (!o.custom) {
            const spanNames = (d.span === 'sel' && sel && sel.length) ? sel : sp.order;
            const mk = sp.key + '|' + d.kind + '|' + spanNames.join(','); // the span extremes only depend on the direction kind + the parts, not on the stops
            const memo = sp._span || (sp._span = {});
            if (memo[mk]) { o.qmin = memo[mk][0]; o.qmax = memo[mk][1]; }
            else {
                let mn = 1e30, mx = -1e30;
                spanNames.forEach(n => {
                    const r = sp.parts[n]; if (!r) return;
                    const N = r.mask.length;
                    for (let k = 0; k < N; k++) if (r.mask[k]) { const q = o.cu * r.U[k] + o.cz * r.Z[k] + o.ca * r.A[k]; if (q < mn) mn = q; if (q > mx) mx = q; }
                });
                if (!(mx > mn)) { mn = 0; mx = 1; }
                memo[mk] = [mn, mx]; o.qmin = mn; o.qmax = mx;
            }
        }
        o.inv = 1 / Math.max(1e-9, o.qmax - o.qmin);
        o.sig = [o.kind, o.rev ? 1 : 0, o.c0, o.cu, o.cz, o.ca, o.qmin, o.qmax].join('|');
        return o;
    }
    function tAtIndex(o, r, k) {
        let t = ((o.c0 + o.cu * r.U[k] + o.cz * r.Z[k] + o.ca * r.A[k]) - o.qmin) * o.inv;
        if (o.rev) t = 1 - t;
        return t < 0 ? 0 : (t > 1 ? 1 : t);
    }

    // ---------------------------------------------------------------- stops (JS mirror of engine/rev_fade_layer.py: same maths, same rounding rules)
    // stop: { p: 0..1, color: [r,g,b] | null, spec: [m, r, cc] | null }  (a finish stop has neither: its colour / spec come from the engine's render)
    const CC_FLOOR = 16, R_FLOOR = 15, CHROME_M = 240;
    function sortStops(stops) { return stops.slice().sort((a, b) => a.p - b.p); }
    function stopValue(stops, t, pick) { // piecewise-linear value of pick(stop) (an array) at t; null when a bracketing stop has no value
        const n = stops.length;
        if (t <= stops[0].p) return pick(stops[0]);
        if (t >= stops[n - 1].p) return pick(stops[n - 1]);
        for (let i = 0; i < n - 1; i++) {
            const a = stops[i], b = stops[i + 1];
            if (t >= a.p && t <= b.p) {
                const va = pick(a), vb = pick(b); if (!va || !vb) return null;
                const s = b.p > a.p ? (t - a.p) / (b.p - a.p) : 1, out = new Array(va.length);
                for (let c = 0; c < va.length; c++) out[c] = va[c] + (vb[c] - va[c]) * s;
                return out;
            }
        }
        return null;
    }
    // CLEARCOAT RULE (iRacing B channel: 0-15 = no clearcoat, 16 = max gloss, 255 = dull): a stop's CC is raised to 16 BEFORE the blend (the iron rule
    // every SPB material obeys), so the ramp is a clean 16 -> 255 (or 255 -> 16) line. Interpolating the raw 0 -> 160 of the Chrome preset and flooring
    // afterwards would hold a flat 16 for the first tenth of the fade and then ramp.
    function specOf(stop) { const s = stop.spec; return s ? [s[0], s[1], Math.max(CC_FLOOR, s[2])] : null; }
    function floorSpec(m, r, cc) { return [m, m < CHROME_M ? Math.max(r, R_FLOOR) : r, Math.max(cc, CC_FLOOR)]; }
    function makeLut(stops) { // colour LUT (LUT_N entries, RGB bytes) + spec LUT (M, R, CC) or null
        const st = sortStops(stops), col = new Uint8Array(LUT_N * 3), hasSpec = st.every(s => !!s.spec), spec = hasSpec ? new Uint8Array(LUT_N * 3) : null;
        const colOf = s => s.color || null;
        for (let i = 0; i < LUT_N; i++) {
            const t = i / (LUT_N - 1), c = stopValue(st, t, colOf);
            if (c) { col[i * 3] = Math.round(c[0]); col[i * 3 + 1] = Math.round(c[1]); col[i * 3 + 2] = Math.round(c[2]); }
            if (spec) { const v = stopValue(st, t, specOf); if (v) { const f = floorSpec(v[0], v[1], v[2]); spec[i * 3] = Math.round(f[0]); spec[i * 3 + 1] = Math.round(f[1]); spec[i * 3 + 2] = Math.round(f[2]); } }
        }
        return { col, spec, hasColor: st.every(s => !!s.color) };
    }

    // ---------------------------------------------------------------- preview image (the on-canvas overlay). stride 1 = full resolution; 4 while dragging
    // Speed: the position of every pixel along the fade (a 10-bit index) is cached per part for the current direction / span / parts, so a stop or
    // colour edit is one LUT read + one 32-bit write per pixel; only a direction change recomputes the index (and drags do that at stride 4).
    // compact pixel list of a part (built once): kk = index inside the part's bbox arrays (mask / U / Z / A), ss = offset on the W x H sheet
    function compact(sp, r) {
        if (r._cp) return r._cp;
        const W = sp.W, N = r.mask.length; let n = 0;
        for (let k = 0; k < N; k++) if (r.mask[k]) n++;
        const kk = new Uint32Array(n), ss = new Uint32Array(n); let j = 0;
        for (let y = r.bb[1]; y <= r.bb[3]; y++) {
            const ry = (y - r.bb[1]) * r.w;
            for (let x = r.bb[0]; x <= r.bb[2]; x++) { const k = ry + x - r.bb[0]; if (r.mask[k]) { kk[j] = k; ss[j] = y * W + x; j++; } }
        }
        r._cp = { n, kk, ss, sub: {} }; return r._cp;
    }
    // the compact list decimated to every stride-th pixel (stride > 1): jj = index into the compact list, oo = offset inside the (W/stride) wide output
    function compactStride(sp, r, stride) {
        const cp = compact(sp, r); if (stride <= 1) return null;
        if (cp.sub[stride]) return cp.sub[stride];
        const W = sp.W, w = Math.ceil(W / stride); let m = 0;
        for (let j = 0; j < cp.n; j++) { const s = cp.ss[j]; if (((s % W) % stride === 0) && (((s / W) | 0) % stride === 0)) m++; }
        const jj = new Uint32Array(m), oo = new Uint32Array(m); let q = 0;
        for (let j = 0; j < cp.n; j++) { const s = cp.ss[j], x = s % W, y = (s / W) | 0; if (x % stride === 0 && y % stride === 0) { jj[q] = j; oo[q] = ((y / stride) | 0) * w + ((x / stride) | 0); q++; } }
        return (cp.sub[stride] = { n: m, jj, oo });
    }
    function tIndex(sp, o, r) {
        const c = r._tc; if (c && c.sig === o.sig) return c.ti;
        const cp = compact(sp, r), n = cp.n, kk = cp.kk, ti = new Uint16Array(n), sc = LUT_N - 1, c0 = o.c0, cu = o.cu, cz = o.cz, ca = o.ca, qm = o.qmin, iv = o.inv, rev = o.rev, U = r.U, Z = r.Z, A = r.A;
        for (let j = 0; j < n; j++) {
            const k = kk[j];
            let t = ((c0 + cu * U[k] + cz * Z[k] + ca * A[k]) - qm) * iv;
            if (rev) t = 1 - t;
            ti[j] = t <= 0 ? 0 : (t >= 1 ? sc : (t * sc + 0.5) | 0);
        }
        r._tc = { sig: o.sig, ti }; return ti;
    }
    // parts: names to fill; returns { img: ImageData, ms, w, h }. Pixels outside the selected parts / clip stay transparent.
    function preview(sp, dir, parts, stops, opts) {
        const stride = (opts && opts.stride) || 1, clip = opts && opts.clip, paintOn = !opts || opts.paint !== false;
        const t0 = (root.performance || Date).now(), W = sp.W, H = sp.H, w = Math.ceil(W / stride), h = Math.ceil(H / stride);
        const img = (opts && opts.into && opts.into.width === w && opts.into.height === h) ? opts.into : new ImageData(w, h), d = img.data, d32 = new Uint32Array(d.buffer);
        if (!(opts && opts.keep)) d.fill(0);
        const o = prepare(sp, dir, (dir && dir.span === 'sel') ? parts : null), L = makeLut(stops), col = L.col, spec = L.spec;
        const lut32 = new Uint32Array(LUT_N), alp = new Float32Array(1);
        const useCol = paintOn && L.hasColor;
        for (let i = 0; i < LUT_N; i++) {
            if (useCol) lut32[i] = (255 << 24) | (col[i * 3 + 2] << 16) | (col[i * 3 + 1] << 8) | col[i * 3];
            else if (spec) { const g = Math.min(255, 70 + spec[i * 3] * 0.55) | 0; lut32[i] = (217 << 24) | ((g + 8 > 255 ? 255 : g + 8) << 16) | (g << 8) | g; }
            else lut32[i] = (128 << 24) | (150 << 16) | (140 << 8) | 140;
        }
        const aScale = useCol ? 1 : (spec ? 217 / 255 : 128 / 255);
        parts.forEach(n => {
            const r = sp.parts[n]; if (!r) return;
            const ti = tIndex(sp, o, r), cp = compact(sp, r), ss = cp.ss, cs = compactStride(sp, r, stride);
            if (!cs && !clip) { for (let j = 0, m = cp.n; j < m; j++) d32[ss[j]] = lut32[ti[j]]; return; } // the hot path: one gather + one scatter per pixel
            const m = cs ? cs.n : cp.n;
            for (let q = 0; q < m; q++) {
                const j = cs ? cs.jj[q] : q, o32 = cs ? cs.oo[q] : ss[q];
                if (clip) {
                    const a = clip[ss[j]]; if (!a) continue;
                    if (a < 255) { const v = lut32[ti[j]]; d32[o32] = ((((v >>> 24) * a / 255) | 0) << 24) | (v & 0xffffff); continue; }
                }
                d32[o32] = lut32[ti[j]];
            }
        });
        return { img, ms: ((root.performance || Date).now()) - t0, w, h };
    }

    // ---------------------------------------------------------------- payload data: t-field (16 bit, 1/4 resolution, parts dilated) + coverage
    // returns { bbox:[x,y,w,h] (document px), ts: scale, tw, th, t16: Uint16Array(tw*th), cov: Uint8Array(w*h) } or null when nothing is covered.
    function field(sp, dir, parts, clip, opts) {
        const W = sp.W, H = sp.H, ts = (opts && opts.ts) || 4;
        let bx0 = W, by0 = H, bx1 = -1, by1 = -1;
        const act = parts.map(n => sp.parts[n]).filter(Boolean);
        act.forEach(r => { bx0 = Math.min(bx0, r.bb[0]); by0 = Math.min(by0, r.bb[1]); bx1 = Math.max(bx1, r.bb[2]); by1 = Math.max(by1, r.bb[3]); });
        if (bx1 < 0) return null;
        bx0 = bx0 - (bx0 % ts); by0 = by0 - (by0 % ts); // align the low-res grid to the document
        const bw = Math.min(W, Math.ceil((bx1 + 1) / ts) * ts) - bx0, bh = Math.min(H, Math.ceil((by1 + 1) / ts) * ts) - by0, tw = Math.ceil(bw / ts), th = Math.ceil(bh / ts); // bw, bh = exact multiples of ts (W, H are)
        const o = prepare(sp, dir, (dir && dir.span === 'sel') ? parts : null);
        const cov = new Uint8Array(bw * bh), t16 = new Uint16Array(tw * th), done = new Uint8Array(tw * th);
        let any = false;
        // coverage (full res): selected parts x clip
        act.forEach(r => {
            for (let y = r.bb[1]; y <= r.bb[3]; y++) {
                const ry = (y - r.bb[1]) * r.w, cy = (y - by0) * bw;
                for (let x = r.bb[0]; x <= r.bb[2]; x++) {
                    if (!r.mask[ry + x - r.bb[0]]) continue;
                    const a = clip ? clip[y * W + x] : 255; if (!a) continue;
                    const ci = cy + x - bx0; if (a > cov[ci]) { cov[ci] = a; any = true; }
                }
            }
        });
        if (!any) return null;
        // t at the centre of every low-res cell: exact part first, then dilated (so the bilinear upsample never reads another island's value)
        for (let pass = 0; pass < 2; pass++) {
            act.forEach(r => {
                const M = pass === 0 ? r.mask : r.dil;
                for (let j = 0; j < th; j++) {
                    const y = by0 + j * ts + (ts >> 1); if (y < r.bb[1] || y > r.bb[3]) continue;
                    for (let i = 0; i < tw; i++) {
                        const ti = j * tw + i; if (done[ti]) continue;
                        const x = bx0 + i * ts + (ts >> 1); if (x < r.bb[0] || x > r.bb[2]) continue;
                        const k = (y - r.bb[1]) * r.w + (x - r.bb[0]);
                        if (!M[k]) continue;
                        t16[ti] = Math.round(tAtIndex(o, r, k) * 65535); done[ti] = 1;
                    }
                }
            });
        }
        return { bbox: [bx0, by0, bw, bh], ts, tw, th, t16, cov, qmin: o.qmin, qmax: o.qmax };
    }

    // [SPB-REV-FADE 2026-10-10 FADE-2] preview of a FROZEN fade (one that came back from a saved project): drawn from the very t-field and coverage the engine receives
    // (fz = { bbox:[x,y,w,h], ts, tw, th, t16:Uint16Array(tw*th), cov:Uint8Array(w*h) }), not from the car model, so the overlay equals the render by construction.
    // The t-field is the 1/4-resolution grid of cell centres written by field(); it is read back with a bilinear sample (clamped at the edge). opts: stride, into, keep, clip
    // (weights 0..255 per sheet pixel, e.g. the decal mask), paint (false = spec-only look). Same LUT as preview().
    function previewField(sp, fz, stops, opts) {
        const stride = (opts && opts.stride) || 1, clip = opts && opts.clip, paintOn = !opts || opts.paint !== false;
        const t0 = (root.performance || Date).now(), W = sp.W, H = sp.H, w = Math.ceil(W / stride), h = Math.ceil(H / stride);
        const img = (opts && opts.into && opts.into.width === w && opts.into.height === h) ? opts.into : new ImageData(w, h), d = img.data, d32 = new Uint32Array(d.buffer);
        if (!(opts && opts.keep)) d.fill(0);
        if (!fz || !fz.cov) return { img, ms: 0, w, h };
        const L = makeLut(stops), col = L.col, spec = L.spec, lut32 = new Uint32Array(LUT_N), useCol = paintOn && L.hasColor;
        for (let i = 0; i < LUT_N; i++) {
            if (useCol) lut32[i] = (255 << 24) | (col[i * 3 + 2] << 16) | (col[i * 3 + 1] << 8) | col[i * 3];
            else if (spec) { const g = Math.min(255, 70 + spec[i * 3] * 0.55) | 0; lut32[i] = (217 << 24) | ((g + 8 > 255 ? 255 : g + 8) << 16) | (g << 8) | g; }
            else lut32[i] = (128 << 24) | (150 << 16) | (140 << 8) | 140;
        }
        const bx = fz.bbox[0], by = fz.bbox[1], bw = fz.bbox[2], bh = fz.bbox[3], ts = fz.ts, tw = fz.tw, th = fz.th, t16 = fz.t16, cov = fz.cov, sc = (LUT_N - 1) / 65535;
        const half = ts / 2, ix0 = new Int32Array(bw), ix1 = new Int32Array(bw), fx = new Float32Array(bw);
        for (let x = 0; x < bw; x++) { const g = (x - half + 0.5) / ts, i0 = Math.floor(g); fx[x] = g - i0; ix0[x] = Math.max(0, Math.min(tw - 1, i0)); ix1[x] = Math.max(0, Math.min(tw - 1, i0 + 1)); }
        for (let y = by; y < by + bh; y += stride) {
            const ry = y - by, g = (ry - half + 0.5) / ts, j0 = Math.floor(g), fy = g - j0, r0 = Math.max(0, Math.min(th - 1, j0)) * tw, r1 = Math.max(0, Math.min(th - 1, j0 + 1)) * tw, cy = ry * bw, oy = ((y / stride) | 0) * w;
            for (let x = bx; x < bx + bw; x += stride) {
                const rx = x - bx; let a = cov[cy + rx]; if (!a) continue;
                if (clip) { const c = clip[y * W + x]; if (!c) continue; if (c < 255) a = (a * c / 255) | 0; if (!a) continue; }
                const a0 = ix0[rx], a1 = ix1[rx], f = fx[rx];
                const top = t16[r0 + a0] + (t16[r0 + a1] - t16[r0 + a0]) * f, bot = t16[r1 + a0] + (t16[r1 + a1] - t16[r1 + a0]) * f;
                let k = ((top + (bot - top) * fy) * sc + 0.5) | 0; if (k < 0) k = 0; else if (k >= LUT_N) k = LUT_N - 1;
                const v = lut32[k];
                d32[oy + ((x / stride) | 0)] = a < 255 ? ((((v >>> 24) * a / 255) | 0) << 24) | (v & 0xffffff) : v;
            }
        }
        return { img, ms: ((root.performance || Date).now()) - t0, w, h };
    }

    root.SpbRevFade = Object.assign(root.SpbRevFade || {}, {
        version: VER, off, ready: () => !off() && !!CUR, build, cur: () => CUR, prepare, tAtIndex, makeLut, preview, previewField, field, stopValue, floorSpec, specOf, sortStops,
        CONST: K, LUT_N, FRONT, _internal: { compute, upFill, dilate, projRange, axisNormal, bboxOf }
    });
})(typeof window !== 'undefined' ? window : globalThis);
