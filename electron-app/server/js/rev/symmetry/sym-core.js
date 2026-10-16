/* [SPB-REV-SYM 2026-10-10] REV-SYMMETRY core - car-aware registration between mirrored parts of ONE iRacing paint sheet.
 *
 * The paint is a flat 2048x2048 UV sheet of the whole car cut open: the left and right side panels sit in different places,
 * mirrored and slightly different in scale / shape; hood, roof, trunk and bumpers are separate islands that are each
 * mirror-symmetric about the car's centre line. This module finds, for the loaded car,
 *   - PAIR maps  : left side <-> right side (and any 'left X' / 'right X' parts the car map knows), both directions;
 *   - SELF maps  : the reflection of a centre part (hood, roof, trunk, bumpers, spoiler, bed, tailgate) about its centre line.
 * Each map = affine (6 params) + an optional free-form displacement grid (FFD) refined on the template's own panel lines.
 *
 * Inputs: the car map part masks (SpbProCar.maskFor, full-res rims) for the silhouettes, the PSD's "Wire" template layer
 * for the interior panel lines. Pipeline per map: 4 axis flips scored by silhouette chamfer -> trimmed ICP on the silhouette
 * (tau 40 -> 4 px) -> trimmed ICP on silhouette + wire lines (tau 6 -> 2 px) -> FFD on the residuals (kept only if it helps).
 * Error = distance from every mapped source edge pixel to the nearest target edge pixel (median / p90 px).
 * Cached per car (memory + localStorage 'spb_rev_sym_reg_v1', keyed by the car layout signature + wire hash).
 *
 * KILL SWITCH: window.SPB_REV_SYM_OFF = true or localStorage SPB_REV_SYM_OFF = '1' -> SpbRevSym.ready() is false and
 * every REV-SYMMETRY tool is inert (the app behaves exactly as before).
 */
(function (root) {
    'use strict';
    const VER = 'sym2.3';
    const LS = 'spb_rev_sym_reg_v1';
    const MEM = {};
    let BUSY = null;

    // [SPB-REV-SYM2 2026-10-10] the switch is read fresh on every call (window flag first, then localStorage), so it works before boot, after boot
    // and live in both directions; a flag set to the text 'false' / '0' / 'off' counts as NOT set (a stray string used to switch it on).
    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_SYM_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_SYM_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_SYM_OFF); }
    }

    // ---------------------------------------------------------------- affine helpers  T = [a,b,c,d,e,f]: x'=a x+b y+c, y'=d x+e y+f
    function ap(T, x, y) { return [T[0] * x + T[1] * y + T[2], T[3] * x + T[4] * y + T[5]]; }
    function inv(T) {
        const det = T[0] * T[4] - T[1] * T[3];
        if (!det) return null;
        const a = T[4] / det, b = -T[1] / det, d = -T[3] / det, e = T[0] / det;
        return [a, b, -(a * T[2] + b * T[5]), d, e, -(d * T[2] + e * T[5])];
    }
    function mul(A, B) { // A o B
        return [A[0] * B[0] + A[1] * B[3], A[0] * B[1] + A[1] * B[4], A[0] * B[2] + A[1] * B[5] + A[2],
            A[3] * B[0] + A[4] * B[3], A[3] * B[1] + A[4] * B[4], A[3] * B[2] + A[4] * B[5] + A[5]];
    }
    function det(T) { return T[0] * T[4] - T[1] * T[3]; }

    // ---------------------------------------------------------------- masks / edges
    function bboxOf(mask, W, H) {
        let x0 = W, y0 = H, x1 = -1, y1 = -1, n = 0;
        for (let y = 0; y < H; y++) {
            const r = y * W;
            for (let x = 0; x < W; x++) if (mask[r + x]) { n++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        }
        return n ? { x0, y0, x1, y1, n } : null;
    }
    // edge pixels inside a region R=[x0,y0,x1,y1] (inclusive) : silhouette boundary of `mask` (+ wire lines near the mask)
    function edgeField(mask, wire, W, H, bb, pad, withWire) {
        const x0 = Math.max(0, bb.x0 - pad), y0 = Math.max(0, bb.y0 - pad), x1 = Math.min(W - 1, bb.x1 + pad), y1 = Math.min(H - 1, bb.y1 + pad);
        const w = x1 - x0 + 1, h = y1 - y0 + 1, f = new Uint8Array(w * h);
        let nb = 0, nw = 0;
        for (let y = y0; y <= y1; y++) {
            for (let x = x0; x <= x1; x++) {
                const i = y * W + x, m = mask[i];
                let v = 0;
                if (m) {
                    if (x === 0 || y === 0 || x === W - 1 || y === H - 1 || !mask[i - 1] || !mask[i + 1] || !mask[i - W] || !mask[i + W]) { v = 1; nb++; }
                }
                if (!v && withWire && wire && wire[i] >= 96) {
                    // a wire pixel counts when it lies on / within 2 px of this part (not on a neighbouring island)
                    if (m || (x > 1 && mask[i - 2]) || (x < W - 2 && mask[i + 2]) || (y > 1 && mask[i - 2 * W]) || (y < H - 2 && mask[i + 2 * W])) { v = 2; nw++; }
                }
                f[(y - y0) * w + (x - x0)] = v;
            }
        }
        return { x0, y0, w, h, f, nb, nw };
    }

    // ---------------------------------------------------------------- exact squared EDT with nearest-feature index (Felzenszwalb-Huttenlocher)
    const BIG = 1e20;
    function edt1(f, n, d, arg, v, z) {
        let k = -1;
        for (let q = 0; q < n; q++) {
            if (f[q] >= BIG) continue; // never a minimum
            if (k < 0) { k = 0; v[0] = q; z[0] = -Infinity; z[1] = Infinity; continue; }
            let s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]);
            while (s <= z[k]) { k--; s = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k]); }
            k++; v[k] = q; z[k] = s; z[k + 1] = Infinity;
        }
        if (k < 0) { for (let q = 0; q < n; q++) { d[q] = BIG; arg[q] = 0; } return; }
        k = 0;
        for (let q = 0; q < n; q++) {
            while (z[k + 1] < q) k++;
            const p = v[k];
            d[q] = (q - p) * (q - p) + f[p]; arg[q] = p;
        }
    }
    function edt(field, mode) { // mode: 1 = silhouette only, 3 = silhouette + wire
        const w = field.w, h = field.h, F = field.f, n = Math.max(w, h);
        const colD = new Float64Array(w * h), colArg = new Int32Array(w * h);
        const f = new Float64Array(n), d = new Float64Array(n), arg = new Int32Array(n), v = new Int32Array(n), z = new Float64Array(n + 1);
        for (let x = 0; x < w; x++) {
            for (let y = 0; y < h; y++) { const c = F[y * w + x]; f[y] = (c && (mode === 3 || c === 1)) ? 0 : BIG; }
            edt1(f, h, d, arg, v, z);
            for (let y = 0; y < h; y++) { colD[y * w + x] = d[y]; colArg[y * w + x] = arg[y]; }
        }
        const D = new Float32Array(w * h), NX = new Int32Array(w * h), NY = new Int32Array(w * h);
        for (let y = 0; y < h; y++) {
            const r = y * w;
            for (let x = 0; x < w; x++) f[x] = colD[r + x];
            edt1(f, w, d, arg, v, z);
            for (let x = 0; x < w; x++) { const ax = arg[x]; D[r + x] = d[x]; NX[r + x] = ax + field.x0; NY[r + x] = colArg[r + ax] + field.y0; }
        }
        return { x0: field.x0, y0: field.y0, w, h, D, NX, NY };
    }
    function look(dt, x, y) { // nearest target edge for a mapped point; null outside the field
        const ix = Math.round(x) - dt.x0, iy = Math.round(y) - dt.y0;
        if (ix < 0 || iy < 0 || ix >= dt.w || iy >= dt.h) return null;
        const i = iy * dt.w + ix;
        if (dt.D[i] >= 1e19) return null;
        return i;
    }

    // ---------------------------------------------------------------- source edge points
    function pointsOf(field, mode, maxN) {
        let n = 0;
        const F = field.f;
        for (let i = 0; i < F.length; i++) if (F[i] && (mode === 3 || F[i] === 1)) n++;
        const stride = Math.max(1, Math.ceil(n / maxN)), m = Math.ceil(n / stride) + 1, out = new Float32Array(m * 2), ty = new Uint8Array(m);
        let k = 0, c = 0;
        for (let y = 0; y < field.h; y++) for (let x = 0; x < field.w; x++) {
            const v = F[y * field.w + x];
            if (v && (mode === 3 || v === 1)) { if (c++ % stride === 0) { ty[k >> 1] = v; out[k++] = x + field.x0; out[k++] = y + field.y0; } }
        }
        const r = out.subarray(0, k); r.types = ty.subarray(0, k >> 1); return r;
    }

    // ---------------------------------------------------------------- map = affine + optional FFD grid on the source bbox
    function ffdAt(G, x, y, p) {
        const gx = (x - G.x0) / G.sx, gy = (y - G.y0) / G.sy;
        const ix = Math.max(0, Math.min(G.nx - 2, Math.floor(gx))), iy = Math.max(0, Math.min(G.ny - 2, Math.floor(gy)));
        const tx = Math.max(0, Math.min(1, gx - ix)), ty = Math.max(0, Math.min(1, gy - iy));
        const i00 = iy * G.nx + ix, i01 = i00 + 1, i10 = i00 + G.nx, i11 = i10 + 1;
        const w00 = (1 - tx) * (1 - ty), w01 = tx * (1 - ty), w10 = (1 - tx) * ty, w11 = tx * ty;
        p[0] += G.dx[i00] * w00 + G.dx[i01] * w01 + G.dx[i10] * w10 + G.dx[i11] * w11;
        p[1] += G.dy[i00] * w00 + G.dy[i01] * w01 + G.dy[i10] * w10 + G.dy[i11] * w11;
    }
    function mapPt(M, x, y) {
        const p = ap(M.A, x, y);
        const L = M.ffd;
        if (L) for (let i = 0; i < L.length; i++) ffdAt(L[i], x, y, p);
        return p;
    }

    // weighted least-squares affine from pairs (p -> q)
    function solveAffine(P, Q, Wt, n) {
        let sxx = 0, sxy = 0, sx = 0, syy = 0, sy = 0, s1 = 0, bx0 = 0, bx1 = 0, bx2 = 0, by0 = 0, by1 = 0, by2 = 0;
        for (let i = 0; i < n; i++) {
            const w = Wt[i], x = P[2 * i], y = P[2 * i + 1], u = Q[2 * i], v = Q[2 * i + 1];
            sxx += w * x * x; sxy += w * x * y; sx += w * x; syy += w * y * y; sy += w * y; s1 += w;
            bx0 += w * x * u; bx1 += w * y * u; bx2 += w * u; by0 += w * x * v; by1 += w * y * v; by2 += w * v;
        }
        const M = [sxx, sxy, sx, sxy, syy, sy, sx, sy, s1];
        const s = solve3(M, [bx0, bx1, bx2]), t = solve3(M, [by0, by1, by2]);
        return (s && t) ? [s[0], s[1], s[2], t[0], t[1], t[2]] : null;
    }
    function solve3(M, b) {
        const a = M.slice(), r = b.slice();
        for (let c = 0; c < 3; c++) {
            let p = c; for (let i = c + 1; i < 3; i++) if (Math.abs(a[i * 3 + c]) > Math.abs(a[p * 3 + c])) p = i;
            if (Math.abs(a[p * 3 + c]) < 1e-12) return null;
            if (p !== c) { for (let j = 0; j < 3; j++) { const t = a[c * 3 + j]; a[c * 3 + j] = a[p * 3 + j]; a[p * 3 + j] = t; } const t = r[c]; r[c] = r[p]; r[p] = t; }
            for (let i = 0; i < 3; i++) if (i !== c) { const f = a[i * 3 + c] / a[c * 3 + c]; for (let j = c; j < 3; j++) a[i * 3 + j] -= f * a[c * 3 + j]; r[i] -= f * r[c]; }
        }
        return [r[0] / a[0], r[1] / a[4], r[2] / a[8]];
    }

    // trimmed ICP, affine
    function icp(pts, A0, dt, taus) {
        let A = A0.slice();
        const n = pts.length / 2, P = new Float32Array(pts.length), Q = new Float32Array(pts.length), Wt = new Float32Array(n);
        let last = null;
        for (let it = 0; it < taus.length; it++) {
            const tau = taus[it], tau2 = tau * tau;
            let m = 0, se = 0;
            for (let i = 0; i < n; i++) {
                const x = pts[2 * i], y = pts[2 * i + 1], q = ap(A, x, y), k = look(dt, q[0], q[1]);
                if (k === null) continue;
                const d2 = dt.D[k];
                if (d2 > tau2) continue;
                P[2 * m] = x; P[2 * m + 1] = y; Q[2 * m] = dt.NX[k]; Q[2 * m + 1] = dt.NY[k];
                const r = d2 / tau2; Wt[m] = (1 - r) * (1 - r); // Tukey-like
                se += d2; m++;
            }
            if (m < 12) break;
            const A2 = solveAffine(P, Q, Wt, m);
            if (!A2) break;
            A = A2; last = { inliers: m, rms: Math.sqrt(se / m), tau };
        }
        return { A, last };
    }

    // FFD refinement, coarse -> fine: each level adds a displacement grid on the source bbox = regularised, smoothed residuals
    // of the trimmed correspondences (outline points weigh 3x: they are unambiguous; panel lines may have no counterpart)
    const FFD_LEVELS = [{ nx: 9, taus: [14, 11, 9, 8] }, { nx: 17, taus: [7, 6, 5, 5] }, { nx: 33, taus: [4, 4, 3, 3] }];
    function ffdLevels(M, pts, dt, bb) {
        const n = pts.length / 2, ty = pts.types, levels = [], trial = { A: M.A, ffd: levels };
        const bw = bb.x1 - bb.x0 + 1, bh = bb.y1 - bb.y0 + 1;
        FFD_LEVELS.forEach(L => {
            const nx = L.nx, ny = Math.max(3, Math.min(L.nx, Math.round((L.nx - 1) * bh / bw) + 1));
            const sx = bw / (nx - 1), sy = bh / (ny - 1);
            const G = { x0: bb.x0, y0: bb.y0, sx, sy, nx, ny, dx: new Float32Array(nx * ny), dy: new Float32Array(nx * ny) };
            levels.push(G);
            L.taus.forEach(tau => {
                const tau2 = tau * tau, N = nx * ny, ax = new Float64Array(N), ay = new Float64Array(N), aw = new Float64Array(N);
                for (let i = 0; i < n; i++) {
                    const x = pts[2 * i], y = pts[2 * i + 1], q = mapPt(trial, x, y), k = look(dt, q[0], q[1]);
                    if (k === null || dt.D[k] > tau2) continue;
                    const rx = dt.NX[k] - q[0], ry = dt.NY[k] - q[1], wt = (ty && ty[i] === 1 ? 3 : 1) * (1 - dt.D[k] / tau2);
                    const gx = (x - G.x0) / sx, gy = (y - G.y0) / sy;
                    const ix = Math.max(0, Math.min(nx - 2, Math.floor(gx))), iy = Math.max(0, Math.min(ny - 2, Math.floor(gy)));
                    const tx = Math.max(0, Math.min(1, gx - ix)), tyy = Math.max(0, Math.min(1, gy - iy));
                    const ws = [(1 - tx) * (1 - tyy), tx * (1 - tyy), (1 - tx) * tyy, tx * tyy], is = [iy * nx + ix, iy * nx + ix + 1, (iy + 1) * nx + ix, (iy + 1) * nx + ix + 1];
                    for (let j = 0; j < 4; j++) { const w = ws[j] * wt; ax[is[j]] += w * rx; ay[is[j]] += w * ry; aw[is[j]] += w; }
                }
                const ux = new Float32Array(N), uy = new Float32Array(N);
                for (let i = 0; i < N; i++) { const w = aw[i]; ux[i] = w > 0 ? ax[i] / (w + 6) : 0; uy[i] = w > 0 ? ay[i] / (w + 6) : 0; }
                for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
                    let sxx = 0, syy = 0, c = 0;
                    for (let b = -1; b <= 1; b++) for (let a = -1; a <= 1; a++) {
                        const ii = i + a, jj = j + b; if (ii < 0 || jj < 0 || ii >= nx || jj >= ny) continue;
                        const w = (a === 0 && b === 0) ? 4 : ((a === 0 || b === 0) ? 2 : 1);
                        sxx += w * ux[jj * nx + ii]; syy += w * uy[jj * nx + ii]; c += w;
                    }
                    G.dx[j * nx + i] += sxx / c; G.dy[j * nx + i] += syy / c;
                }
            });
        });
        return levels;
    }

    // error stats of a map over ALL source edge points against the target edge field, split by kind:
    //   outline = the part silhouette (unambiguous), lines = the Wire template's panel/mesh lines.
    //   matched = a counterpart within 6 px (beyond that the other side genuinely differs there: a fuel cap, a plate notch ...)
    function errStats(M, pts, dt) {
        const n = pts.length / 2, ty = pts.types, acc = { 1: [], 2: [] }, far = { 1: 0, 2: 0 };
        let miss = 0, tsum = 0, tn = 0;
        for (let i = 0; i < n; i++) {
            const q = mapPt(M, pts[2 * i], pts[2 * i + 1]), k = look(dt, q[0], q[1]), t = ty ? ty[i] : 1;
            if (k === null) { miss++; continue; }
            const d = Math.sqrt(dt.D[k]);
            tsum += Math.min(d, 5); tn++;
            if (d > 6) far[t]++; else acc[t].push(d);
        }
        const st = (t) => {
            const ds = acc[t].sort((a, b) => a - b), tot = ds.length + far[t];
            const q = (f) => ds.length ? Math.round(ds[Math.min(ds.length - 1, Math.floor(ds.length * f))] * 100) / 100 : null;
            let s = 0; for (const d of ds) s += d;
            return { n: tot, matched: tot ? Math.round(ds.length / tot * 1000) / 1000 : null, median: q(0.5), p90: q(0.9), mean: ds.length ? Math.round(s / ds.length * 100) / 100 : null };
        };
        return { outline: st(1), lines: st(2), tmean: tn ? Math.round(tsum / tn * 1000) / 1000 : null, miss };
    }

    // ---------------------------------------------------------------- one directed registration A -> B (B may equal A for a self map)
    // 2026-10-10 (sym2.2): the mirror axis of an island = the line its mask overlaps its own reflection best (run-length, every 2nd
    // line). The bbox centre is NOT the axis when the island carries a one-sided tab: ARCA trunk bbox centre 1196.5 vs true axis
    // ~1175 (outline 925..1425); ICP never recovered (the 43 px edge gap is beyond its first trim radius), so the stripe sat 22 px
    // off the trunk's centre line. kind 'V' = reflect y (returns cy), 'H' = reflect x (returns cx).
    function reflCentre(mask, W, bb, kind) {
        const vert = kind === 'V', a0 = vert ? bb.x0 : bb.y0, a1 = vert ? bb.x1 : bb.y1, b0 = vert ? bb.y0 : bb.x0, b1 = vert ? bb.y1 : bb.x1;
        const lo = 2 * b0, hi = 2 * b1, acc = new Float64Array(hi - lo + 1);
        for (let a = a0; a <= a1; a += 2) {
            const runs = []; let s = -1;
            for (let b = b0; b <= b1 + 1; b++) { const v = b <= b1 && (vert ? mask[b * W + a] : mask[a * W + b]); if (v && s < 0) s = b; if (!v && s >= 0) { runs.push(s, b - 1); s = -1; } }
            for (let i = 0; i < runs.length; i += 2) for (let j = 0; j < runs.length; j += 2) {
                const p0 = runs[i], p1 = runs[i + 1], q0 = runs[j], q1 = runs[j + 1]; // overlap of [p0,p1] with [c2-q1, c2-q0]
                for (let c2 = p0 + q0; c2 <= p1 + q1; c2++) { const o = Math.min(p1, c2 - q0) - Math.max(p0, c2 - q1) + 1; if (o > 0) acc[c2 - lo] += o; }
            }
        }
        let best = -1, bc = (b0 + b1) / 2, mid = b0 + b1;
        for (let k = 0; k < acc.length; k++) { const c2 = k + lo; if (acc[k] > best || (acc[k] === best && Math.abs(c2 - mid) < Math.abs(2 * bc - mid))) { best = acc[k]; bc = c2 / 2; } }
        return bc;
    }
    function flipAbout(bb, kind, ctr) { // flip inside the source bbox (self maps: about the island's own mirror axis, ctr)
        const cx = (ctr && ctr.H != null) ? ctr.H : (bb.x0 + bb.x1) / 2, cy = (ctr && ctr.V != null) ? ctr.V : (bb.y0 + bb.y1) / 2;
        if (kind === 'H') return [-1, 0, 2 * cx, 0, 1, 0];
        if (kind === 'V') return [1, 0, 0, 0, -1, 2 * cy];
        if (kind === 'HV') return [-1, 0, 2 * cx, 0, -1, 2 * cy];
        return [1, 0, 0, 0, 1, 0];
    }
    function boxMap(a, b) { // scale/translate bbox a onto bbox b
        const sx = (b.x1 - b.x0 + 1) / (a.x1 - a.x0 + 1), sy = (b.y1 - b.y0 + 1) / (a.y1 - a.y0 + 1);
        return [sx, 0, b.x0 - sx * a.x0, 0, sy, b.y0 - sy * a.y0];
    }
    function chamfer(A, pts, dt) {
        const n = pts.length / 2; let s = 0, c = 0;
        for (let i = 0; i < n; i += 3) {
            const q = ap(A, pts[2 * i], pts[2 * i + 1]), k = look(dt, q[0], q[1]);
            s += k === null ? 900 : Math.min(900, dt.D[k]); c++;
        }
        return c ? Math.sqrt(s / c) : 1e9;
    }
    // 2026-10-10 (sym2.2) self maps only: maximum-consensus refinement of the mirror axis. ICP settles between the island's
    // outline (which carries one-sided lips) and the Wire template's mesh (mirror-symmetric about the model's centre seam) and can
    // leave the axis a few px off + tilted (ARCA trunk: affine axis 1175 + shear 0.019 vs the mesh's centre seam 1180; roof tilt
    // 5 px over its length). Search axis offset d (px) x tilt t (rad) for the reflection that lands the most edge points
    // within 2 px of an edge on the other side; lips simply stay unmatched. Coarse 25x9 grid, then a fine 9x5 grid.
    function consensus(A, pts, dt, bb, kind) {
        const cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2, n = pts.length / 2;
        const score = (B) => { let s = 0; for (let i = 0; i < n; i += 2) { const q = ap(B, pts[2 * i], pts[2 * i + 1]), k = look(dt, q[0], q[1]); if (k !== null && dt.D[k] <= 4) s++; } return s; };
        const make = (d, t) => {
            const Tr = kind === 'H' ? [1, 0, 2 * d, 0, 1, 0] : [1, 0, 0, 0, 1, 2 * d];
            const c = Math.cos(2 * t), s = Math.sin(2 * t), R = [c, -s, cx - c * cx + s * cy, s, c, cy - s * cx - c * cy];
            return mul(R, mul(Tr, A));
        };
        let best = { d: 0, t: 0, s: score(A) }; const s0 = best.s;
        const run = (ds, ts) => ds.forEach(d => ts.forEach(t => { const s = score(make(d, t)); if (s > best.s || (s === best.s && Math.abs(d) + 400 * Math.abs(t) < Math.abs(best.d) + 400 * Math.abs(best.t))) best = { d, t, s }; }));
        const rng = (a, b, st) => { const o = []; for (let v = a; v <= b + 1e-9; v += st) o.push(Math.round(v * 1e5) / 1e5); return o; };
        run(rng(-12, 12, 1), rng(-0.02, 0.02, 0.005));
        const d0 = best.d, t0 = best.t;
        run(rng(d0 - 1, d0 + 1, 0.25), rng(t0 - 0.0025, t0 + 0.0025, 0.00125));
        return { A: make(best.d, best.t), d: best.d, t: best.t, inliers: best.s, inliers0: s0, of: Math.ceil(n / 2) };
    }
    function registerDirected(srcMask, dstMask, wire, W, H, opts) {
        const t0 = Date.now();
        const sb = bboxOf(srcMask, W, H), db = bboxOf(dstMask, W, H);
        if (!sb || !db || sb.n < 500 || db.n < 500) return null;
        const self = srcMask === dstMask;
        const sF = edgeField(srcMask, wire, W, H, sb, 0, true), dF = edgeField(dstMask, wire, W, H, db, 48, true);
        const dtSil = edt(dF, 1), dtAll = edt(dF, 3);
        const silPts = pointsOf(sF, 1, 6000), allPts = pointsOf(sF, 3, 14000), errPts = pointsOf(sF, 3, 60000);
        // 1) candidate flips (self maps: the two mirror axes only)
        const kinds = self ? ['H', 'V'] : ['I', 'H', 'V', 'HV'];
        const ctr = self ? { H: reflCentre(srcMask, W, sb, 'H'), V: reflCentre(srcMask, W, sb, 'V') } : null;
        const cands = kinds.map(k => { const A = mul(boxMap(sb, db), flipAbout(sb, k, ctr)); return { k, A, score: chamfer(A, silPts, dtSil) }; });
        cands.sort((a, b) => a.score - b.score);
        let pick = cands[0];
        if (opts && opts.hint) { const h = cands.find(c => c.k === opts.hint); if (h && h.score <= pick.score * 1.15 + 1) pick = h; }
        // [SPB-REV-SYM2 2026-10-10] opts.plain: the PLAIN FLIP - just the winning flip scaled onto the other part's bounding box (what Flip
        // Horizontal does in any paint program): no ICP, no consensus, no FFD. Used when a car has no Wire template to line the parts up
        // with and the outline-only fit is not trustworthy (see build()); also the reference the experiments compare against.
        if (opts && opts.plain) {
            const eP = errStats({ A: pick.A, ffd: null }, errPts, dtSil);
            return { A: pick.A, ffd: null, flip: pick.k, axis0: ctr, consensus: null, flipScores: cands.map(c => c.k + ':' + Math.round(c.score * 10) / 10).join(' '), hintAgrees: opts.hint ? opts.hint === cands[0].k : null,
                wire: false, plain: true, srcBox: [sb.x0, sb.y0, sb.x1, sb.y1], dstBox: [db.x0, db.y0, db.x1, db.y1], errAffine: eP, errFfd: null, err: eP, det: Math.round(det(pick.A) * 1000) / 1000, ms: Date.now() - t0 };
        }
        // 2) silhouette ICP, 3) silhouette + wire ICP
        const s1 = icp(silPts, pick.A, dtSil, [40, 32, 25, 20, 16, 12, 10, 8, 6, 5, 4, 4, 4]);
        const useWire = sF.nw > 200 && dF.nw > 200;
        const s2 = useWire ? icp(allPts, s1.A, dtAll, [6, 6, 5, 5, 4, 4, 3, 3, 3, 2.5, 2.5, 2.5, 2, 2, 2]) : s1;
        const dtErr = useWire ? dtAll : dtSil;
        const cons = (self && (pick.k === 'V' || pick.k === 'H')) ? consensus(s2.A, errPts, dtErr, sb, pick.k) : null;
        const M = { A: (cons && cons.inliers > cons.inliers0) ? cons.A : s2.A, ffd: null };
        const eAff = errStats(M, errPts, dtErr);
        // 4) coarse-to-fine FFD on the residuals - kept only when it lowers the truncated mean error by >= 5 %
        let eF = null;
        if (!(opts && opts.noFfd)) {
            const G = ffdLevels(M, useWire ? allPts : silPts, dtErr, sb);
            const M2 = { A: M.A, ffd: G };
            eF = errStats(M2, errPts, dtErr);
            if (eF.tmean != null && eAff.tmean != null && eF.tmean <= eAff.tmean * 0.99) M.ffd = G;
        }
        return {
            A: M.A, ffd: M.ffd ? M.ffd.map(packFfd) : null, flip: pick.k, axis0: ctr, consensus: cons ? { d: cons.d, t: cons.t, inliers: cons.inliers, inliers0: cons.inliers0, of: cons.of } : null, flipScores: cands.map(c => c.k + ':' + Math.round(c.score * 10) / 10).join(' '),
            hintAgrees: opts && opts.hint ? opts.hint === cands[0].k : null, wire: useWire, srcBox: [sb.x0, sb.y0, sb.x1, sb.y1], dstBox: [db.x0, db.y0, db.x1, db.y1],
            errAffine: eAff, errFfd: eF, err: M.ffd ? eF : eAff, ffdTried: eF ? eF.tmean : null, det: Math.round(det(M.A) * 1000) / 1000, ms: Date.now() - t0
        };
    }
    function packFfd(G) { return { x0: G.x0, y0: G.y0, sx: G.sx, sy: G.sy, nx: G.nx, ny: G.ny, dx: Array.from(G.dx, v => Math.round(v * 100) / 100), dy: Array.from(G.dy, v => Math.round(v * 100) / 100) }; }
    function unpack(R) { if (!R) return null; return { A: R.A, ffd: R.ffd ? R.ffd.map(g => ({ x0: g.x0, y0: g.y0, sx: g.sx, sy: g.sy, nx: g.nx, ny: g.ny, dx: Float32Array.from(g.dx), dy: Float32Array.from(g.dy) })) : null }; }

    // ---------------------------------------------------------------- car inputs
    function canvasWH() { const c = document.getElementById('paintCanvas'); return c ? [c.width, c.height] : [2048, 2048]; }
    function layers() { try { return root._psdLayers || (typeof _psdLayers !== 'undefined' ? _psdLayers : []); } catch (e) { return []; } }
    function wireLayer() { return layers().find(l => l && l.img && /(^|\s)(wire|wireframe)(\s|$)/i.test(String(l.name || '').trim())) || null; }
    function wireAlpha(W, H) {
        const L = wireLayer(); if (!L) return null;
        const c = document.createElement('canvas'); c.width = W; c.height = H;
        const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(L.img, L.bbox ? L.bbox[0] : 0, L.bbox ? L.bbox[1] : 0);
        const d = x.getImageData(0, 0, W, H).data, a = new Uint8Array(W * H);
        for (let i = 0; i < W * H; i++) a[i] = d[i * 4 + 3];
        return a;
    }
    function hashArr(a, step) { let h = 0x811c9dc5; for (let i = 0; i < a.length; i += step) { h ^= a[i]; h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
    const SELF_PARTS = ['hood', 'roof', 'trunk', 'front bumper', 'rear bumper', 'spoiler', 'bed', 'tailgate', 'top wing', 'tank'];
    function partList() { try { return (root.SpbProCar && root.SpbProCar.parts && root.SpbProCar.parts()) || []; } catch (e) { return []; } }
    function partInfo(name) { try { const m = root.SpbProCar.map(); const b = m && m.boxes && m.boxes[name]; return b ? { front: b.front || null, up: b.up || null } : {}; } catch (e) { return {}; } }
    // the part's MAIN panel: the largest 8-connected component of the car map mask (a box-based part can also hold small
    // neighbouring strips / plates that have no counterpart on the other side; strokes there are not mirrored)
    const MAINC = {};
    function mainComponent(m, W, H) { // labelled inside the mask's bbox only (2026-10-10: first build 5 s -> faster; same result)
        const out = new Uint8Array(W * H), bb = bboxOf(m, W, H);
        if (!bb) return out;
        const bw = bb.x1 - bb.x0 + 1, bh = bb.y1 - bb.y0 + 1, N = bw * bh, lab = new Int32Array(N), stack = new Int32Array(N);
        const at = (x, y) => m[(y + bb.y0) * W + x + bb.x0];
        let best = 0, bestN = 0, cur = 0;
        for (let i = 0; i < N; i++) {
            if (lab[i] || !at(i % bw, (i / bw) | 0)) continue;
            cur++; let sp = 0, n = 0; stack[sp++] = i; lab[i] = cur;
            while (sp) {
                const p = stack[--sp]; n++;
                const x = p % bw, y = (p / bw) | 0;
                for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
                    if (!dx && !dy) continue;
                    const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= bw || yy >= bh) continue;
                    const q = yy * bw + xx; if (!lab[q] && at(xx, yy)) { lab[q] = cur; stack[sp++] = q; }
                }
            }
            if (n > bestN) { bestN = n; best = cur; }
        }
        for (let i = 0; i < N; i++) if (lab[i] === best) out[((i / bw) | 0) * W + bb.y0 * W + (i % bw) + bb.x0] = 255;
        return out;
    }
    function maskOf(name) {
        try {
            const r = root.SpbProCar.maskFor(name); if (!r || !r.mask || r.empty) return null;
            const [W, H] = canvasWH(), k = name + '|' + hashArr(r.mask, 331);
            if (!MAINC[k]) MAINC[k] = mainComponent(r.mask, W, H);
            return MAINC[k];
        } catch (e) { return null; }
    }
    function carKey(W, H, wa) {
        let sig = '';
        try { sig = (root.SpbProCar.layoutSig && root.SpbProCar.layoutSig()) || ''; } catch (e) {}
        if (!sig) try { sig = String(root.SpbProCar.signature && root.SpbProCar.signature() || ''); } catch (e) {}
        return VER + '|' + W + 'x' + H + '|' + String(sig).slice(0, 80) + '|' + partList().join(',') + '|' + (wa ? hashArr(wa, 97) : 'nowire');
    }

    // expected sheet flip between the two side panels from the car library's nose / roof-line flags
    function sideHint(a, b) {
        const A = partInfo(a), B = partInfo(b);
        if (!A.front || !B.front) return null;
        const h = (A.front === B.front) ? '' : 'H', v = (A.up && B.up && A.up !== B.up) ? 'V' : '';
        return (h + v) || 'I';
    }
    function selfHint(name) {
        const f = partInfo(name).front;
        if (f === 'left' || f === 'right') return 'V';
        if (f === 'top' || f === 'bottom') return 'H';
        return null;
    }

    // ---------------------------------------------------------------- public: build (or load) the registration of the loaded car
    function load(key) {
        if (MEM[key]) return MEM[key];
        try { const all = JSON.parse(root.localStorage.getItem(LS) || '{}'); if (all[key]) { MEM[key] = all[key]; MEM[key].fromCache = 'localStorage'; return MEM[key]; } } catch (e) {}
        return null;
    }
    function save(key, reg) {
        MEM[key] = reg;
        try { const all = JSON.parse(root.localStorage.getItem(LS) || '{}'); all[key] = reg; const ks = Object.keys(all); while (ks.length > 8) delete all[ks.shift()]; root.localStorage.setItem(LS, JSON.stringify(all)); } catch (e) {}
    }
    let CUR = null; // { key, reg, maps:{...}, partMap }
    function compile(key, reg, W, H) {
        const maps = {}, masks = {};
        (reg.pairs || []).forEach(p => {
            maps[p.a + '>' + p.b] = { from: p.a, to: p.b, M: unpack(p.ab), self: false };
            maps[p.b + '>' + p.a] = { from: p.b, to: p.a, M: unpack(p.ba), self: false };
        });
        (reg.selfs || []).forEach(s => { maps[s.part + '>' + s.part] = { from: s.part, to: s.part, M: unpack(s.map), self: true }; });
        // part id map: which registered part owns each pixel (first part listed wins)
        const names = [];
        (reg.pairs || []).forEach(p => { names.push(p.a, p.b); });
        (reg.selfs || []).forEach(s => names.push(s.part));
        const pm = new Uint8Array(W * H);
        names.forEach((nm, i) => { const m = maskOf(nm); if (!m) return; masks[nm] = m; for (let k = 0; k < m.length; k++) if (m[k] && !pm[k]) pm[k] = i + 1; });
        CUR = { key, reg, maps, names, partMap: pm, masks, W, H };
        return CUR;
    }
    // [SPB-REV-SYM2 2026-10-10] A car WITHOUT a Wire layer is registered from its outlines alone (window and wheel openings are part of a
    // part's outline, so this fits well: on 3 cars that DO have a Wire, hiding it left the lines within median 1 px / p90 3-4 px of the real
    // Wire, same as the Wire-assisted fit - symmetry2/data/acc_nowire.json). The fit's own numbers cannot prove it, so each map is gated:
    //   matched  = share of outline points within 6 px of an edge on the other part, tmean = truncated mean error, SIZE = how far the two
    //   panels' boxes differ (side pairs only). Calibration (t_nowire_gate.py, 19 right fits on 3 cars vs 11 deliberately wrong pairings):
    //   right fits matched 0.518-1.0, tmean 0.21-3.17, pair size within a few %; wrong pairings matched 0.247-0.607, tmean 2.47-4.14,
    //   size far apart. (A correct plain flip of an ARCA / G6 side pair reports matched 0.20: the lips; its true line error is p90 5 px, so PLAIN_MATCHED is 0.15.)
    //   A map that fails drops to a PLAIN FLIP (the winning flip scaled onto the other part's box, no ICP / FFD) when even
    //   that is plausible (PLAIN_*), else the part is SKIPPED (not mirrored) - never silently wrong; reg.mode / plain / skipped say which.
    const GATE = { MATCHED: 0.45, TMEAN: 3.6, SIZE: 0.10, PLAIN_MATCHED: 0.15, PLAIN_SIZE: 0.25 };
    function sizeDev(r) {
        const s = r && r.srcBox, d = r && r.dstBox; if (!s || !d) return 0;
        const w1 = s[2] - s[0] + 1, h1 = s[3] - s[1] + 1, w2 = d[2] - d[0] + 1, h2 = d[3] - d[1] + 1;
        return Math.max(Math.abs(w1 / w2 - 1), Math.abs(h1 / h2 - 1));
    }
    function gateNoWire(r, ma, mb, W, H, hint, self, G) {
        if (!r) return { r: null, tier: 'none', why: null };
        const o = (r.err && r.err.outline) || {}, tm = r.err ? r.err.tmean : null, sz = self ? 0 : sizeDev(r), why = [];
        if (hint && r.flip !== hint) why.push('the outline and the car library disagree on how it flips');
        if (!(o.matched >= G.MATCHED)) why.push('only ' + Math.round(100 * (o.matched || 0)) + ' % of its outline matches');
        if (!(tm <= G.TMEAN)) why.push('the outline fit is loose');
        if (sz > G.SIZE) why.push('the two panels differ in size by ' + Math.round(sz * 100) + ' %');
        if (!why.length) return { r, tier: 'fit', why: null };
        const pl = registerDirected(ma, mb, null, W, H, { hint, plain: true }), po = (pl && pl.err && pl.err.outline) || {};
        const okPlain = pl && (!hint || pl.flip === hint) && po.matched >= G.PLAIN_MATCHED && sz <= G.PLAIN_SIZE;
        return okPlain ? { r: pl, tier: 'plain', why: why.join('; ') } : { r: null, tier: 'skip', why: why.join('; ') };
    }
    function build(force, bopts) {
        if (off()) return Promise.resolve(null);
        if (BUSY) return BUSY;
        const ensure = (root.SpbProCar && root.SpbProCar.ensure) ? root.SpbProCar.ensure(false) : Promise.resolve(null);
        BUSY = Promise.resolve(ensure).then(() => {
            const [W, H] = canvasWH();
            const wa = wireAlpha(W, H);
            const key = carKey(W, H, wa);
            if (!force && CUR && CUR.key === key) return CUR;
            const test = !!(bopts && bopts.gate), G = Object.assign({}, GATE, test ? bopts.gate : null);   // bopts.gate: test override (nothing cached)
            const cached = (force || test) ? null : load(key);
            if (cached) return compile(key, cached, W, H);
            const t0 = Date.now(), parts = partList(), reg = { v: VER, key, W, H, wire: !!wa, pairs: [], selfs: [], plain: [], skipped: [], mode: 'wire', at: new Date().toISOString() };
            const done = {};
            parts.forEach(a => {
                const m = /^(left|right|driver|passenger)\b\s*(.*)$/i.exec(a);
                if (!m || done[a]) return;
                const want = { left: 'right', right: 'left', driver: 'passenger', passenger: 'driver' }[m[1].toLowerCase()];
                const b = parts.find(p => new RegExp('^' + want + '\\b\\s*' + m[2].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '$', 'i').test(p));
                if (!b || done[b]) return;
                done[a] = done[b] = 1;
                const ma = maskOf(a), mb = maskOf(b);
                if (!ma || !mb) return;
                const hint = sideHint(a, b);
                let ab = registerDirected(ma, mb, wa, W, H, { hint }), tier = 'fit';
                if (!wa) { // no Wire layer: gate the outline-only fit (plain flip / skip when it is not trustworthy)
                    const g = gateNoWire(ab, ma, mb, W, H, hint, false, G); ab = g.r; tier = g.tier;
                    if (tier === 'plain') reg.plain.push(a, b); else if (tier === 'skip') reg.skipped.push({ part: a, why: g.why }, { part: b, why: g.why });
                }
                const ba = ab && fitInverse(ab, ma, mb, wa, W, H);          // B->A = the exact inverse of A->B (round trip ~0)
                if (!ab || !ba) return;
                reg.pairs.push({ a, b, ab, ba, hint, tier, roundTrip: roundTrip(unpack(ab), unpack(ba), ma, W, H) });
            });
            parts.forEach(p => {
                if (done[p] || SELF_PARTS.indexOf(String(p).toLowerCase()) === -1) return;
                const m = maskOf(p); if (!m) return;
                let r = registerDirected(m, m, wa, W, H, { hint: selfHint(p) }), tier = 'fit';
                if (!wa) {
                    const g = gateNoWire(r, m, m, W, H, selfHint(p), true, G); r = g.r; tier = g.tier;
                    if (tier === 'plain') reg.plain.push(p); else if (tier === 'skip') reg.skipped.push({ part: p, why: g.why });
                }
                if (r) reg.selfs.push({ part: p, map: r, hint: selfHint(p), tier });
            });
            // how the car was fitted: 'wire' (template Wire used), 'outline' (no Wire, outline fit passed), 'plain' (some parts fell back to a plain flip),
            // 'partial' (some parts not mirrored), 'none' (nothing to mirror: no left / right panels, hood, roof ... found or none could be trusted)
            reg.mode = (!reg.pairs.length && !reg.selfs.length) ? 'none' : wa ? 'wire' : reg.skipped.length ? 'partial' : reg.plain.length ? 'plain' : 'outline';
            reg.ms = Date.now() - t0;
            if (!test) save(key, reg);
            return compile(key, reg, W, H);
        }).then(c => { BUSY = null; return c; }, e => { BUSY = null; throw e; });
        return BUSY;
    }
    // the inverse of a registered map, fitted on exact pairs (q = map(p) -> p) sampled over the source part: affine + the same
    // coarse-to-fine FFD levels on the target bbox. Error is then measured like a forward map (target edges vs source edge field).
    function fitInverse(R, ma, mb, wa, W, H) {
        const t0 = Date.now(), Mab = unpack(R), sb = bboxOf(ma, W, H), db = bboxOf(mb, W, H);
        const P = [], Q = [];
        for (let y = sb.y0; y <= sb.y1; y += 5) for (let x = sb.x0; x <= sb.x1; x += 5) {
            if (!ma[y * W + x]) continue;
            const q = mapPt(Mab, x, y); P.push(x, y); Q.push(q[0], q[1]);
        }
        const n = P.length / 2, Wt = new Float32Array(n).fill(1);
        const A = solveAffine(Float32Array.from(Q), Float32Array.from(P), Wt, n);
        const levels = [], M = { A, ffd: levels };
        FFD_LEVELS.forEach(L => {
            const bw = db.x1 - db.x0 + 1, bh = db.y1 - db.y0 + 1, nx = L.nx, ny = Math.max(3, Math.min(L.nx, Math.round((L.nx - 1) * bh / bw) + 1));
            const sx = bw / (nx - 1), sy = bh / (ny - 1), N = nx * ny;
            const G = { x0: db.x0, y0: db.y0, sx, sy, nx, ny, dx: new Float32Array(N), dy: new Float32Array(N) };
            levels.push(G);
            for (let r = 0; r < 3; r++) {
                const ax = new Float64Array(N), ay = new Float64Array(N), aw = new Float64Array(N);
                for (let i = 0; i < n; i++) {
                    const x = Q[2 * i], y = Q[2 * i + 1], m = mapPt(M, x, y), rx = P[2 * i] - m[0], ry = P[2 * i + 1] - m[1];
                    const gx = (x - G.x0) / sx, gy = (y - G.y0) / sy;
                    const ix = Math.max(0, Math.min(nx - 2, Math.floor(gx))), iy = Math.max(0, Math.min(ny - 2, Math.floor(gy)));
                    const tx = Math.max(0, Math.min(1, gx - ix)), ty = Math.max(0, Math.min(1, gy - iy));
                    const ws = [(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty], is = [iy * nx + ix, iy * nx + ix + 1, (iy + 1) * nx + ix, (iy + 1) * nx + ix + 1];
                    for (let j = 0; j < 4; j++) { ax[is[j]] += ws[j] * rx; ay[is[j]] += ws[j] * ry; aw[is[j]] += ws[j]; }
                }
                for (let i = 0; i < N; i++) if (aw[i] > 0) { G.dx[i] += ax[i] / (aw[i] + 0.5); G.dy[i] += ay[i] / (aw[i] + 0.5); }
            }
        });
        // forward-style error of the inverse: B's edges mapped into A's edge field
        const bF = edgeField(mb, wa, W, H, db, 0, true), aF = edgeField(ma, wa, W, H, sb, 48, true);
        const useWire = bF.nw > 200 && aF.nw > 200, dt = edt(aF, useWire ? 3 : 1), pts = pointsOf(bF, useWire ? 3 : 1, 60000);
        const e = errStats(M, pts, dt);
        return { A, ffd: levels.map(packFfd), flip: R.flip, inverseOf: true, wire: useWire, srcBox: [db.x0, db.y0, db.x1, db.y1], dstBox: [sb.x0, sb.y0, sb.x1, sb.y1],
            errAffine: e, err: e, det: Math.round(det(A) * 1000) / 1000, ms: Date.now() - t0 };
    }
    function roundTrip(Mab, Mba, ma, W, H) {
        const ds = []; let mx = 0;
        for (let i = 0; i < ma.length; i += 997) {
            if (!ma[i]) continue;
            const x = i % W, y = (i / W) | 0, q = mapPt(Mab, x, y), r = mapPt(Mba, q[0], q[1]), d = Math.hypot(r[0] - x, r[1] - y);
            ds.push(d); if (d > mx) mx = d;
        }
        ds.sort((a, b) => a - b);
        return { n: ds.length, median: ds.length ? Math.round(ds[ds.length >> 1] * 100) / 100 : null, max: Math.round(mx * 100) / 100 };
    }

    // ---------------------------------------------------------------- queries used by the tools
    function partAt(x, y) {
        if (!CUR) return null;
        const xi = Math.round(x), yi = Math.round(y);
        if (xi < 0 || yi < 0 || xi >= CUR.W || yi >= CUR.H) return null;
        const v = CUR.partMap[yi * CUR.W + xi];
        return v ? CUR.names[v - 1] : null;
    }
    function mirrorOf(part) { // the map from `part` to its mirror (pair partner, else its own reflection)
        if (!CUR || !part) return null;
        const pr = (CUR.reg.pairs || []).find(p => p.a === part || p.b === part);
        if (pr) return CUR.maps[part + '>' + (pr.a === part ? pr.b : pr.a)];
        return CUR.maps[part + '>' + part] || null;
    }
    // local linear part (Jacobian) of a map at a point, by finite differences
    function jac(M, x, y) {
        const p = mapPt(M, x, y), px = mapPt(M, x + 1, y), py = mapPt(M, x, y + 1);
        return [px[0] - p[0], py[0] - p[0], px[1] - p[1], py[1] - p[1]];
    }
    function summary() {
        if (!CUR) return null;
        const r = CUR.reg;
        return {
            key: r.key, ms: r.ms, wire: r.wire, mode: r.mode || 'wire', plain: r.plain || [], skipped: r.skipped || [], fromCache: r.fromCache || null,
            pairs: (r.pairs || []).map(p => ({ a: p.a, b: p.b, flip: p.ab.flip, hint: p.hint, hintAgrees: p.ab.hintAgrees, det: p.ab.det, ffd: !!p.ab.ffd, errAB: p.ab.err, errBA: p.ba.err, errAffineAB: p.ab.errAffine, ffdTriedAB: p.ab.ffdTried, roundTrip: p.roundTrip, ms: p.ab.ms + p.ba.ms })),
            selfs: (r.selfs || []).map(s => ({ part: s.part, flip: s.map.flip, hint: s.hint, det: s.map.det, ffd: !!s.map.ffd, err: s.map.err, errAffine: s.map.errAffine, ms: s.map.ms }))
        };
    }

    root.SpbRevSym = {
        version: VER, off, build, ready: () => !off() && !!CUR, cur: () => CUR, summary, partAt, mirrorOf, mapPt, jac, ap, inv, mul, det,
        _internal: { registerDirected, edgeField, edt, errStats, bboxOf, maskOf, wireAlpha, unpack, pointsOf, gateNoWire, GATE },
        clearCache: () => { CUR = null; for (const k in MEM) delete MEM[k]; try { root.localStorage.removeItem(LS); } catch (e) {} }
    };
})(typeof window !== 'undefined' ? window : globalThis);
