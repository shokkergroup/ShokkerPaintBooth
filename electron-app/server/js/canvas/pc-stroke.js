/* Algorithm ported from PhotoCraft crates/paint/src/{render,lib,retouch}.rs and crates/algo/src/retouch.rs
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript for Shokker Paint Booth canvas layers (typed arrays, Canvas2D ImageData).
 * Lane PORT-W2 (strokes), 2026-10-09. Owner verdict "tools basically SUCK" 2026-10-09.
 *
 * SPBPcStroke = per-stroke COVERAGE BUFFER painting (Photoshop semantics):
 *   - every dab accumulates coverage   c <- c + v*(1-c)       (v = tip shape * flow)   [render.rs Coverage::accumulate]
 *   - the buffer composites ONCE onto the pre-stroke pixels at k = c * opacity * selection  [render.rs composite]
 *     so stroke opacity is a hard cap and overlapping dabs never darken/densify beyond it.
 *   - tip = dab_coverage(): anti-aliased edge + smoothstep hardness falloff, pixel centres at +0.5, so a
 *     fractional dab centre moves the footprint smoothly (sub-pixel dabs).                [lib.rs dab_coverage]
 *   - retouch kernels (dodge/burn tone curves with range + protect tones, gaussian blur, unsharp sharpen)
 *     ported from crates/algo/src/retouch.rs.
 * Disable with window.SPB_PC_W2_OFF = true (callers fall back to the previous engines unchanged).
 */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcStroke = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function enabled() {
        return !(typeof window !== 'undefined' && window.SPB_PC_W2_OFF) &&
            !(typeof globalThis !== 'undefined' && globalThis.SPB_PC_W2_OFF);
    }

    // lib.rs dab_coverage(d, radius, hardness)
    function dabCoverage(d, radius, hardness) {
        if (d >= radius + 0.5) return 0;
        let edge = radius + 0.5 - d;
        edge = edge < 0 ? 0 : (edge > 1 ? 1 : edge);
        const h = hardness < 0 ? 0 : (hardness > 1 ? 1 : hardness);
        const inner = radius * h;
        if (d <= inner || radius - inner < 1e-3) return edge;
        let t = (d - inner) / (radius - inner);
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        return edge * (1 - t * t * (3 - 2 * t));
    }

    // ---- pooled stroke session ------------------------------------------------------------
    // One coverage plane + one "pre-stroke pixels" plane, reused between strokes (cleared by dirty rect).
    const pool = { w: 0, h: 0, cov: null, orig: null };
    let session = null;

    function getSession(key, w, h) {
        if (session && session.key === key && session.w === w && session.h === h) return session;
        if (session && session.dirty) clearDirty(session);
        if (!pool.cov || pool.w !== w || pool.h !== h) {
            pool.w = w; pool.h = h;
            pool.cov = new Float32Array(w * h);
            pool.orig = new Uint8ClampedArray(w * h * 4);
        }
        session = {
            key, w, h, cov: pool.cov, orig: pool.orig,
            dirty: null, // {x0,y0,x1,y1}
            dabs: 0,
        };
        return session;
    }

    function clearDirty(s) {
        const d = s.dirty;
        if (!d) return;
        for (let y = d.y0; y < d.y1; y++) s.cov.fill(0, y * s.w + d.x0, y * s.w + d.x1);
        s.dirty = null;
    }

    function endSession() {
        if (session) clearDirty(session);
        session = null;
    }

    function growDirty(s, x0, y0, x1, y1) {
        const d = s.dirty;
        if (!d) { s.dirty = { x0, y0, x1, y1 }; return; }
        if (x0 < d.x0) d.x0 = x0;
        if (y0 < d.y0) d.y0 = y0;
        if (x1 > d.x1) d.x1 = x1;
        if (y1 > d.y1) d.y1 = y1;
    }

    /**
     * Paint one dab through the stroke coverage buffer.
     * ctx    : CanvasRenderingContext2D-like (getImageData/putImageData) of the layer canvas
     * key    : identity of the stroke surface (the layer canvas object); a new key starts a new stroke
     * o      : { x, y (pixel-index coords, may be fractional), radius, hardness 0..1,
     *            color:[r,g,b] 0..255, cap 0..1 (stroke opacity), flow 0..1 (per-dab), ceil 0..1 (default 1),
     *            erase:bool, footprint:{shape,contains,distanceSquared} (optional, round fast path when shape==='round'),
     *            sel:Uint8Array|null (+selW,selH) selection / alpha-lock mask 0..255 }
     * Returns the damaged rect {x,y,width,height} or null.
     */
    function paintDab(ctx, key, canvasW, canvasH, o) {
        const s = getSession(key, canvasW, canvasH);
        const r = Math.max(0.5, +o.radius || 1);
        const cx = (+o.x) + 0.5, cy = (+o.y) + 0.5;
        const x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        const x1 = Math.min(canvasW, Math.ceil(cx + r + 1)), y1 = Math.min(canvasH, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return null;
        const rw = x1 - x0, rh = y1 - y0;
        const img = ctx.getImageData(x0, y0, rw, rh);
        const px = img.data;
        const hardness = o.hardness == null ? 1 : o.hardness;
        const flow = Math.max(0, Math.min(1, o.flow == null ? 1 : o.flow));
        const ceil = o.ceil == null ? 1 : Math.max(0, Math.min(1, o.ceil));
        const cap = Math.max(0, Math.min(1, o.cap == null ? 1 : o.cap));
        const fp = o.footprint && o.footprint.shape !== 'round' ? o.footprint : null;
        const sel = o.sel || null, selW = o.selW || canvasW, selH = o.selH || canvasH;
        const erase = !!o.erase;
        const tile = o.tile || null;
        const col = o.color || [0, 0, 0];
        const cr = col[0], cg = col[1], cb = col[2];
        const cov = s.cov, orig = s.orig, W = s.w;
        // [STROKE-HL 2026-10-12] owner: "when I try to color in an area using the brush in the SOURCE BOX it should be coloring it a
        // highlighted color ... at the exact same time so you can see where you are drawing". o.hlOut = Uint8ClampedArray(W*H): the brush's
        // FOOTPRINT coverage (stroke coverage x selection, ignoring opacity/tile alpha so a 10% brush is still visible). Display-only: the
        // layer pixels, undo and renders never read it (js/canvas/pc-strokehl.js owns the overlay).
        const hl = (!erase && o.hlOut && o.hlOut.length >= W * s.h) ? o.hlOut : null;
        let touched = false;
        for (let yy = 0; yy < rh; yy++) {
            const y = y0 + yy;
            const dy = y + 0.5 - cy;
            for (let xx = 0; xx < rw; xx++) {
                const x = x0 + xx;
                const dx = x + 0.5 - cx;
                let v;
                if (fp) {
                    // Shaped tips (square/diamond/slash/noise): integer offset from the rounded centre, SPB footprint rules.
                    const ix = x - Math.round(o.x), iy = y - Math.round(o.y);
                    if (!fp.contains(ix, iy, ix * ix + iy * iy)) continue;
                    v = o.aliased ? 1 : softFall(fp.distanceSquared(ix, iy), r, hardness);
                } else {
                    const d2 = dx * dx + dy * dy;
                    const lim = (r + 0.5) * (r + 0.5);
                    if (d2 >= lim) continue;
                    v = dabCoverage(Math.sqrt(d2), r, hardness);
                }
                if (v <= 0) continue;
                const gi = y * W + x;
                const c = cov[gi];
                const nv = c + v * flow * (ceil - c);
                if (!(nv > c)) continue;
                const pi = (yy * rw + xx) * 4, oi = gi * 4;
                if (c === 0) {
                    orig[oi] = px[pi]; orig[oi + 1] = px[pi + 1]; orig[oi + 2] = px[pi + 2]; orig[oi + 3] = px[pi + 3];
                }
                cov[gi] = nv;
                let k = nv * cap;
                if (sel) {
                    const sv = (x < selW && y < selH) ? sel[y * selW + x] : 0;
                    if (sv < 255) k *= sv / 255;
                }
                if (hl) { // [STROKE-HL 2026-10-12] footprint coverage within the selection (cap/opacity ignored on purpose)
                    const hv = (k > 0 && cap > 0) ? Math.min(1, k / cap) : 0;
                    const hb = (hv * 255 + 0.5) | 0;
                    if (hb > hl[gi]) hl[gi] = hb;
                }
                if (k > 1) k = 1;
                const da = orig[oi + 3] / 255;
                if (erase) {
                    px[pi] = orig[oi]; px[pi + 1] = orig[oi + 1]; px[pi + 2] = orig[oi + 2];
                    px[pi + 3] = Math.round(orig[oi + 3] * (1 - k));
                    if (o.fpOut) o.fpOut[gi] = k; // [SPECIAL-ZONE 2026-10-11] eraser weight (removes from the zone's Special footprint)
                } else {
                    // renderer over_native: straight-alpha source-over at weight k
                    // PORT-W5: o.tile = {data,w,h} world-anchored tiled source (Special / pattern brush) instead of a flat colour
                    let sr = cr, sg = cg, sb = cb, kk = k;
                    if (tile) {
                        const ti = (((y % tile.h) + tile.h) % tile.h * tile.w + ((x % tile.w) + tile.w) % tile.w) * 4;
                        sr = tile.data[ti]; sg = tile.data[ti + 1]; sb = tile.data[ti + 2]; kk = k * tile.data[ti + 3] / 255;
                    }
                    if (o.fpOut) o.fpOut[gi] = kk; // [SPECIAL-SPEC 2026-10-11] the paint's own per-pixel weight, for the spec footprint
                    const oa = kk + da * (1 - kk);
                    if (oa > 0) {
                        const wd = da * (1 - kk);
                        px[pi] = Math.round((sr * kk + orig[oi] * wd) / oa);
                        px[pi + 1] = Math.round((sg * kk + orig[oi + 1] * wd) / oa);
                        px[pi + 2] = Math.round((sb * kk + orig[oi + 2] * wd) / oa);
                        px[pi + 3] = Math.round(oa * 255);
                    }
                }
                touched = true;
            }
        }
        if (!touched) return null;
        ctx.putImageData(img, x0, y0);
        growDirty(s, x0, y0, x1, y1);
        s.dabs++;
        return { x: x0, y: y0, width: rw, height: rh };
    }


    /**
     * Same coverage-buffer dab, but over a plain RGBA array (paintImageData.data) and with a SOURCE image
     * (clone stamp, history brush): k = coverage * cap * selection; dst = source-over(src, srcAlpha*k) on the PRE-stroke pixels.
     * key  : identity of the stroke (e.g. the per-stroke clone source snapshot). pre : pre-stroke RGBA (optional; else lazily kept).
     * o    : { x, y (centre, may be fractional), radius, hardness, cap, flow, ceil, footprint, sel, selW, selH,
     *          src: RGBA array, sdx, sdy: integer source offset (src pixel = dst pixel + offset) }
     * Returns damaged rect or null.
     */
    function paintDabData(data, W, H, key, o) {
        const s = getSession(key, W, H);
        const r = Math.max(0.5, +o.radius || 1);
        const cx = (+o.x) + 0.5, cy = (+o.y) + 0.5;
        const x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        const x1 = Math.min(W, Math.ceil(cx + r + 1)), y1 = Math.min(H, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return null;
        const hardness = o.hardness == null ? 1 : o.hardness;
        const flow = Math.max(0, Math.min(1, o.flow == null ? 1 : o.flow));
        const ceil = o.ceil == null ? 1 : Math.max(0, Math.min(1, o.ceil));
        const cap = Math.max(0, Math.min(1, o.cap == null ? 1 : o.cap));
        const fp = o.footprint && o.footprint.shape !== 'round' ? o.footprint : null;
        const sel = o.sel || null, selW = o.selW || W;
        const pre = o.pre || s.orig, src = o.src, sdx = o.sdx | 0, sdy = o.sdy | 0;
        const cov = s.cov;
        let touched = false;
        for (let y = y0; y < y1; y++) {
            const dy = y + 0.5 - cy;
            const sy = y + sdy;
            if (src && (sy < 0 || sy >= H)) continue;
            for (let x = x0; x < x1; x++) {
                const dx = x + 0.5 - cx;
                let v;
                if (fp) {
                    const ix = x - Math.round(o.x), iy = y - Math.round(o.y);
                    if (!fp.contains(ix, iy, ix * ix + iy * iy)) continue;
                    v = o.aliased ? 1 : softFall(fp.distanceSquared(ix, iy), r, hardness);
                } else if (o.aliased) {
                    // PORT-W5: aliased tip (Pencil): a pixel is in or out by its centre, no AA ring
                    const d2 = dx * dx + dy * dy;
                    if (d2 > r * r + 1e-6 && !(r <= 0.5 && d2 < 1e-6)) continue;
                    v = 1;
                } else {
                    const d2 = dx * dx + dy * dy;
                    if (d2 >= (r + 0.5) * (r + 0.5)) continue;
                    v = dabCoverage(Math.sqrt(d2), r, hardness);
                }
                if (v <= 0) continue;
                const sx = x + sdx;
                if (src && (sx < 0 || sx >= W)) continue;
                const gi = y * W + x;
                const c = cov[gi];
                const nv = c + v * flow * (ceil - c);
                if (!(nv > c) && !(o.refresh && !window.SPB_TFX2_OFF)) continue; // [SPB-TFX2 2026-10-09 TA-008] refresh: re-composite already-covered pixels
                const di = gi * 4;
                if (c === 0 && pre === s.orig) { pre[di] = data[di]; pre[di + 1] = data[di + 1]; pre[di + 2] = data[di + 2]; pre[di + 3] = data[di + 3]; }
                cov[gi] = nv;
                let k = nv * cap;
                if (sel) { const sv = sel[y * selW + x]; if (sv < 255) k *= sv / 255; }
                if (k <= 0) continue;
                if (k > 1) k = 1;
                const si = src ? (sy * W + sx) * 4 : di;
                const sa = (src ? src[si + 3] : 255) / 255 * k;
                const da = pre[di + 3] / 255;
                if (o.color) {
                    // PORT-W5: solid colour source (Colour Brush) - same composite as the layer Brush
                    const oa0 = k + da * (1 - k);
                    if (oa0 > 0) {
                        const wd0 = da * (1 - k);
                        data[di] = Math.round((o.color[0] * k + pre[di] * wd0) / oa0);
                        data[di + 1] = Math.round((o.color[1] * k + pre[di + 1] * wd0) / oa0);
                        data[di + 2] = Math.round((o.color[2] * k + pre[di + 2] * wd0) / oa0);
                        data[di + 3] = Math.round(oa0 * 255);
                    }
                    touched = true;
                    continue;
                }
                if (o.mix) {
                    // PORT-W5: History Brush - restore the saved pixel INCLUDING alpha (retouch.rs mix_premultiplied)
                    const sA = src[si + 3] / 255, oa1 = da + (sA - da) * k;
                    for (let ch = 0; ch < 3; ch++) {
                        const dv = pre[di + ch], sv = src[si + ch];
                        data[di + ch] = oa1 > 1e-6 ? Math.round((dv * da + (sv * sA - dv * da) * k) / oa1) : Math.round(dv + (sv - dv) * k);
                    }
                    data[di + 3] = Math.round(oa1 * 255);
                    touched = true;
                    continue;
                }
                if (o.keepAlpha) {
                    // colour-only mix (recolor): destination alpha untouched
                    data[di] = Math.round(pre[di] + (src[si] - pre[di]) * sa);
                    data[di + 1] = Math.round(pre[di + 1] + (src[si + 1] - pre[di + 1]) * sa);
                    data[di + 2] = Math.round(pre[di + 2] + (src[si + 2] - pre[di + 2]) * sa);
                    data[di + 3] = pre[di + 3];
                    touched = true;
                    continue;
                }
                const oa = sa + da * (1 - sa);
                if (oa > 0) {
                    const wd = da * (1 - sa);
                    data[di] = Math.round((src[si] * sa + pre[di] * wd) / oa);
                    data[di + 1] = Math.round((src[si + 1] * sa + pre[di + 1] * wd) / oa);
                    data[di + 2] = Math.round((src[si + 2] * sa + pre[di + 2] * wd) / oa);
                    data[di + 3] = Math.round(oa * 255);
                }
                touched = true;
            }
        }
        if (!touched) return null;
        growDirty(s, x0, y0, x1, y1);
        s.dabs++;
        return { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
    }


    /**
     * Sequential retouch dab (apply_dab_stroke): edits `data` (RGBA array) in place, dab n sees dab n-1.
     * o: { mode:'dodge'|'burn'|'blur'|'sharpen', x, y (fractional ok), radius, hardness,
     *      amount 0..1 (exposure*flow / blur strength / sharpen strength), range 0|1|2 (shadows/mid/highlights),
     *      protect:bool, sigma (blur), sel, selW, footprint }
     * Returns damaged rect or null.
     */
    function retouchDab(data, W, H, o) {
        const r = Math.max(0.5, +o.radius || 1);
        const cx = (+o.x) + 0.5, cy = (+o.y) + 0.5;
        const x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        const x1 = Math.min(W, Math.ceil(cx + r + 1)), y1 = Math.min(H, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return null;
        const hardness = o.hardness == null ? 1 : o.hardness;
        const amount = Math.max(0, Math.min(1, +o.amount || 0));
        const fp = o.footprint && o.footprint.shape !== 'round' ? o.footprint : null;
        const sel = o.sel || null, selW = o.selW || W;
        const mode = o.mode, ww = x1 - x0, wh = y1 - y0;
        const win = { x: x0, y: y0, width: ww, height: wh };
        let blurred = null;
        // [SPB-TFX2 2026-10-09 TA-010] sharpen: o.sigma (USM radius), o.gain (amount multiplier) and o.protectR (detail-protect window
        // radius) are caller-supplied so the tool scales with brush size/strength; absent = the PORT-W2 behaviour (sigma 1, 3x3, gain 1).
        const shSigma = (mode === 'sharpen' && o.sigma > 0) ? o.sigma : 1.0;
        const shGain = (mode === 'sharpen' && o.gain > 0) ? o.gain : 1;
        const prR = (mode === 'sharpen' && o.protectR >= 1) ? Math.min(8, Math.round(o.protectR)) : 1;
        if (mode === 'blur') blurred = localBlur(data, W, H, win, Math.max(0.5, o.sigma || 1.5));
        else if (mode === 'sharpen') blurred = localBlur(data, W, H, win, shSigma);
        const c3 = [0, 0, 0];
        // sharpen reads the pre-dab (2R+1)^2 neighbourhood range: snapshot window + R px halo, then separable min/max per channel
        let snap = null, mnA = null, mxA = null;
        const sx0 = Math.max(0, x0 - prR), sy0 = Math.max(0, y0 - prR), sx1 = Math.min(W, x1 + prR), sy1 = Math.min(H, y1 + prR), sw = sx1 - sx0, sh = sy1 - sy0;
        if (mode === 'sharpen') {
            snap = new Uint8ClampedArray(sw * sh * 4);
            for (let yy = sy0; yy < sy1; yy++) snap.set(data.subarray((yy * W + sx0) * 4, (yy * W + sx1) * 4), (yy - sy0) * sw * 4);
            if (prR > 1) {   // separable window min/max (O(n*R)) instead of an R^2 loop per pixel per channel
                const tmpMn = new Uint8Array(sw * sh * 3), tmpMx = new Uint8Array(sw * sh * 3);
                mnA = new Uint8Array(sw * sh * 3); mxA = new Uint8Array(sw * sh * 3);
                for (let yy = 0; yy < sh; yy++) for (let xx = 0; xx < sw; xx++) {
                    const xa = xx - prR < 0 ? 0 : xx - prR, xb = xx + prR >= sw ? sw - 1 : xx + prR;
                    for (let ch = 0; ch < 3; ch++) {
                        let lo = 255, hi = 0;
                        for (let q = xa; q <= xb; q++) { const v = snap[(yy * sw + q) * 4 + ch]; if (v < lo) lo = v; if (v > hi) hi = v; }
                        const o3 = (yy * sw + xx) * 3 + ch; tmpMn[o3] = lo; tmpMx[o3] = hi;
                    }
                }
                for (let yy = 0; yy < sh; yy++) {
                    const ya = yy - prR < 0 ? 0 : yy - prR, yb = yy + prR >= sh ? sh - 1 : yy + prR;
                    for (let xx = 0; xx < sw; xx++) for (let ch = 0; ch < 3; ch++) {
                        let lo = 255, hi = 0;
                        for (let q = ya; q <= yb; q++) { const o3 = (q * sw + xx) * 3 + ch; if (tmpMn[o3] < lo) lo = tmpMn[o3]; if (tmpMx[o3] > hi) hi = tmpMx[o3]; }
                        const o3 = (yy * sw + xx) * 3 + ch; mnA[o3] = lo; mxA[o3] = hi;
                    }
                }
            }
        }
        let touched = false;
        for (let y = y0; y < y1; y++) {
            const dy = y + 0.5 - cy;
            for (let x = x0; x < x1; x++) {
                const dx = x + 0.5 - cx;
                let v;
                if (fp) {
                    const ix = x - Math.round(o.x), iy = y - Math.round(o.y);
                    if (!fp.contains(ix, iy, ix * ix + iy * iy)) continue;
                    v = softFall(fp.distanceSquared(ix, iy), r, hardness);
                } else {
                    const d2 = dx * dx + dy * dy;
                    if (d2 >= (r + 0.5) * (r + 0.5)) continue;
                    v = dabCoverage(Math.sqrt(d2), r, hardness);
                }
                if (v <= 0) continue;
                if (sel) { const sv = sel[y * selW + x]; if (sv <= 0) continue; if (sv < 255) v *= sv / 255; }
                const di = (y * W + x) * 4;
                if (data[di + 3] === 0) continue;
                const k = v * amount * shGain;
                if (k <= 0) continue;
                if (mode === 'dodge' || mode === 'burn') {
                    c3[0] = data[di] / 255; c3[1] = data[di + 1] / 255; c3[2] = data[di + 2] / 255;
                    const before0 = c3[0], before1 = c3[1], before2 = c3[2];
                    dodgeBurn(c3, k, o.range == null ? 1 : o.range, mode === 'burn', o.protect !== false);
                    data[di] = Math.max(0, Math.min(255, Math.round(c3[0] * 255)));
                    data[di + 1] = Math.max(0, Math.min(255, Math.round(c3[1] * 255)));
                    data[di + 2] = Math.max(0, Math.min(255, Math.round(c3[2] * 255)));
                    void before0; void before1; void before2;
                } else {
                    const bi = ((y - y0) * ww + (x - x0)) * 4;
                    for (let ch = 0; ch < 3; ch++) {
                        const cv = data[di + ch];
                        let nv;
                        if (mode === 'blur') {
                            nv = cv + (blurred[bi + ch] - cv) * (k > 1 ? 1 : k);
                        } else {
                            nv = cv + k * (cv - blurred[bi + ch]);
                            // protect_detail: clamp to the (2R+1)^2 neighbourhood range (no halos / new extremes). R=1 = the PORT-W2 3x3.
                            let lo = cv, hi = cv;
                            if (mnA) {
                                const o3 = ((y - sy0) * sw + (x - sx0)) * 3 + ch;
                                if (mnA[o3] < lo) lo = mnA[o3];
                                if (mxA[o3] > hi) hi = mxA[o3];
                            } else {
                                for (let ny = -1; ny <= 1; ny++) {
                                    const yy = y + ny < 0 ? 0 : (y + ny >= H ? H - 1 : y + ny);
                                    for (let nx = -1; nx <= 1; nx++) {
                                        const xx = x + nx < 0 ? 0 : (x + nx >= W ? W - 1 : x + nx);
                                        const nvv = snap[((yy - sy0) * sw + (xx - sx0)) * 4 + ch];
                                        if (nvv < lo) lo = nvv;
                                        if (nvv > hi) hi = nvv;
                                    }
                                }
                            }
                            nv = nv < lo ? lo : (nv > hi ? hi : nv);
                        }
                        data[di + ch] = nv < 0 ? 0 : (nv > 255 ? 255 : Math.round(nv));
                    }
                }
                touched = true;
            }
        }
        return touched ? win : null;
    }

    function softFall(dist2, radius, hardness) {
        const rr = Math.max(1e-6, radius);
        const n = Math.sqrt(Math.max(0, dist2)) / rr;
        if (n > 1) return 0;
        if (hardness >= 0.999 || n <= hardness) return 1;
        const t = Math.max(0, Math.min(1, (n - hardness) / Math.max(1e-6, 1 - hardness)));
        return 1 - t * t * (3 - 2 * t);
    }

    // ---- retouch kernels (crates/algo/src/retouch.rs) --------------------------------------
    function luma(r, g, b) { return 0.299 * r + 0.587 * g + 0.114 * b; }

    // range: 0 shadows, 1 midtones, 2 highlights
    function toneCurve(v, e, range, burn) {
        if (v < 0) v = 0;
        e = e < 0 ? 0 : (e > 1 ? 1 : e);
        const vc = v > 1 ? 1 : v;
        if (range === 1) {
            let w = 4 * v * (1 - v); w = w < 0 ? 0 : (w > 1 ? 1 : w);
            return burn ? v + w * (Math.pow(vc, 1 + e) - v) : v + w * (Math.pow(vc, 1 / (1 + e)) - v);
        }
        if (range === 0) {
            return burn ? v - e * (1 - vc) * (1 - vc) * v : v + e * (1 - vc) * (1 - vc) * (1 - vc);
        }
        return burn ? v - e * vc * vc * v : v + e * vc * vc * (1 - vc);
    }

    function compressGamut(c, l) {
        l = l < 0 ? 0 : (l > 1 ? 1 : l);
        const lo = Math.min(c[0], c[1], c[2]), hi = Math.max(c[0], c[1], c[2]);
        let t = 1;
        if (hi > 1 && hi - l > 1e-9) t = Math.min(t, (1 - l) / (hi - l));
        if (lo < 0 && l - lo > 1e-9) t = Math.min(t, l / (l - lo));
        c[0] = l + (c[0] - l) * t; c[1] = l + (c[1] - l) * t; c[2] = l + (c[2] - l) * t;
        return c;
    }

    // c: [r,g,b] in 0..1 -> in place
    function dodgeBurn(c, e, range, burn, protect) {
        if (e <= 0) return c;
        if (protect) {
            const l = luma(c[0], c[1], c[2]);
            const nl = toneCurve(l, e, range, burn);
            if (l > 1e-6) { const f = nl / l; c[0] *= f; c[1] *= f; c[2] *= f; } else { c[0] = c[1] = c[2] = nl; }
            return compressGamut(c, nl);
        }
        c[0] = toneCurve(c[0], e, range, burn);
        c[1] = toneCurve(c[1], e, range, burn);
        c[2] = toneCurve(c[2], e, range, burn);
        return c;
    }

    /**
     * Sequential dab edit of a window (apply_dab_stroke): rgba is a Uint8ClampedArray window copy, `fp` gives the
     * per-pixel dab weight. Used by dodge/burn: work' = work + (tone(work) - work) * weight, mixed back at opacity.
     * Returns nothing; caller owns orig/work/mix_back.
     */
    function gaussKernel(sigma) {
        const r = Math.max(1, Math.ceil(sigma * 3));
        const k = new Float32Array(2 * r + 1);
        let sum = 0;
        for (let i = -r; i <= r; i++) { const v = Math.exp(-(i * i) / Math.max(1e-6, 2 * sigma * sigma)); k[i + r] = v; sum += v; }
        for (let i = 0; i < k.length; i++) k[i] /= sum;
        return { k, r };
    }

    /** local_blur: blur window (wx0,wy0,ww,wh) of RGBA buffer (w x h), premultiplied by alpha, edge clamped. Returns Float32Array(ww*wh*4) straight RGBA 0..255. */
    function localBlur(data, w, h, win, sigma) {
        const { k, r } = gaussKernel(sigma);
        const ww = win.width, wh = win.height, x0 = win.x, y0 = win.y;
        const th = wh + 2 * r;
        const tmp = new Float32Array(ww * th * 4);
        for (let ty = 0; ty < th; ty++) {
            let y = y0 + ty - r; y = y < 0 ? 0 : (y >= h ? h - 1 : y);
            for (let ox = 0; ox < ww; ox++) {
                let a0 = 0, a1 = 0, a2 = 0, a3 = 0;
                for (let i = 0; i < k.length; i++) {
                    let x = x0 + ox + i - r; x = x < 0 ? 0 : (x >= w ? w - 1 : x);
                    const p = (y * w + x) * 4, kv = k[i], al = data[p + 3];
                    a0 += data[p] * al * kv; a1 += data[p + 1] * al * kv; a2 += data[p + 2] * al * kv; a3 += al * kv;
                }
                const o = (ty * ww + ox) * 4;
                tmp[o] = a0; tmp[o + 1] = a1; tmp[o + 2] = a2; tmp[o + 3] = a3;
            }
        }
        const out = new Float32Array(ww * wh * 4);
        for (let oy = 0; oy < wh; oy++) {
            for (let ox = 0; ox < ww; ox++) {
                let a0 = 0, a1 = 0, a2 = 0, a3 = 0;
                for (let i = 0; i < k.length; i++) {
                    const s = ((oy + i) * ww + ox) * 4, kv = k[i];
                    a0 += tmp[s] * kv; a1 += tmp[s + 1] * kv; a2 += tmp[s + 2] * kv; a3 += tmp[s + 3] * kv;
                }
                const o = (oy * ww + ox) * 4;
                if (a3 > 1e-6) { out[o] = a0 / a3; out[o + 1] = a1 / a3; out[o + 2] = a2 / a3; }
                else {
                    const p = ((y0 + oy) * w + x0 + ox) * 4;
                    out[o] = data[p]; out[o + 1] = data[p + 1]; out[o + 2] = data[p + 2];
                }
                out[o + 3] = a3;
            }
        }
        return out;
    }


    /**
     * PORT-W5 Smudge (PhotoCraft crates/paint/src/retouch.rs `Smudge`): a premultiplied colour buffer carried from dab to dab.
     * Each dab (1) lays the carried colour down at k = tip * strength via mix_premultiplied, then (2) re-picks-up the pixels
     * under the dab: carry = carry*strength + pixel*(1-strength) over the whole carry square.  `finger` = [r,g,b,a] 0..255
     * starts the stroke with that colour (finger painting).  state: opaque object from smudgeState().
     * o: { x, y (fractional ok), radius, hardness, strength 0..1, sel, selW, footprint, finger }
     */
    function smudgeState(maxRadius) { return { r: Math.ceil(Math.max(1, maxRadius)) + 2, carry: null, side: 0 }; }
    function smudgeDab(data, W, H, st, o) {
        const r = st.r, side = 2 * r + 1;
        const cx = Math.floor((+o.x) + 0.5), cy = Math.floor((+o.y) + 0.5);
        const strength = Math.max(0, Math.min(1, +o.strength || 0));
        const hardness = o.hardness == null ? 1 : o.hardness;
        const rad = Math.max(0.5, +o.radius || 1);
        const fp = o.footprint && o.footprint.shape !== 'round' ? o.footprint : null;
        const sel = o.sel || null, selW = o.selW || W;
        if (!st.carry) {
            const c = new Float32Array(side * side * 4);
            const f = o.finger;
            for (let qy = 0; qy < side; qy++) {
                for (let qx = 0; qx < side; qx++) {
                    const q = (qy * side + qx) * 4;
                    let rr, gg, bb, aa;
                    if (f) { rr = f[0]; gg = f[1]; bb = f[2]; aa = (f[3] == null ? 255 : f[3]) / 255; }
                    else {
                        const x = Math.min(W - 1, Math.max(0, cx + qx - r)), y = Math.min(H - 1, Math.max(0, cy + qy - r));
                        const i = (y * W + x) * 4;
                        rr = data[i]; gg = data[i + 1]; bb = data[i + 2]; aa = data[i + 3] / 255;
                    }
                    c[q] = rr * aa; c[q + 1] = gg * aa; c[q + 2] = bb * aa; c[q + 3] = aa;
                }
            }
            st.carry = c; st.side = side;
        }
        const carry = st.carry;
        const ccx = (+o.x) + 0.5, ccy = (+o.y) + 0.5;
        const x0 = Math.max(0, Math.floor(ccx - rad - 1)), y0 = Math.max(0, Math.floor(ccy - rad - 1));
        const x1 = Math.min(W, Math.ceil(ccx + rad + 1)), y1 = Math.min(H, Math.ceil(ccy + rad + 1));
        let touched = false;
        for (let y = y0; y < y1; y++) {
            const dy = y + 0.5 - ccy;
            for (let x = x0; x < x1; x++) {
                const dx = x + 0.5 - ccx;
                let v;
                if (fp) {
                    const ix = x - Math.round(o.x), iy = y - Math.round(o.y);
                    if (!fp.contains(ix, iy, ix * ix + iy * iy)) continue;
                    v = softFall(fp.distanceSquared(ix, iy), rad, hardness);
                } else {
                    const d2 = dx * dx + dy * dy;
                    if (d2 >= (rad + 0.5) * (rad + 0.5)) continue;
                    v = dabCoverage(Math.sqrt(d2), rad, hardness);
                }
                if (sel) { const sv = sel[y * selW + x]; if (sv <= 0) continue; if (sv < 255) v *= sv / 255; }
                const k = v * strength;
                const qx = x - cx + r, qy = y - cy + r;
                if (k <= 0 || qx < 0 || qy < 0 || qx >= side || qy >= side) continue;
                const q = (qy * side + qx) * 4, ca = carry[q + 3], di = (y * W + x) * 4;
                const da = data[di + 3] / 255, oa = da + (ca - da) * k;
                for (let ch = 0; ch < 3; ch++) {
                    const s = ca > 1e-6 ? carry[q + ch] / ca : carry[q + ch];
                    const dv = data[di + ch];
                    const nv = oa > 1e-6 ? (dv * da + (s * ca - dv * da) * k) / oa : dv + (s - dv) * k;
                    data[di + ch] = nv < 0 ? 0 : (nv > 255 ? 255 : Math.round(nv));
                }
                data[di + 3] = Math.round(oa * 255);
                touched = true;
            }
        }
        // pick up: the carried colour keeps `strength` of itself
        const keep = strength;
        for (let qy = 0; qy < side; qy++) {
            const y = cy + qy - r; if (y < 0 || y >= H) continue;
            for (let qx = 0; qx < side; qx++) {
                const x = cx + qx - r; if (x < 0 || x >= W) continue;
                const q = (qy * side + qx) * 4, di = (y * W + x) * 4, pa = data[di + 3] / 255;
                carry[q] = carry[q] * keep + data[di] * pa * (1 - keep);
                carry[q + 1] = carry[q + 1] * keep + data[di + 1] * pa * (1 - keep);
                carry[q + 2] = carry[q + 2] * keep + data[di + 2] * pa * (1 - keep);
                carry[q + 3] = carry[q + 3] * keep + pa * (1 - keep);
            }
        }
        return touched ? { x: x0, y: y0, width: x1 - x0, height: y1 - y0 } : null;
    }


    /**
     * PORT-W5 mask dab: the stroke coverage buffer applied to a Uint8 zone/spatial MASK (Brush Zone, erase side).
     * The old zone eraser subtracted falloff*opacity from the mask on EVERY overlapping dab, so a 50% eraser at 10% spacing
     * cleared the mask in a few dabs (opacity was not a cap).  Here coverage accumulates per stroke and the result is
     * pre-stroke * (1 - coverage*cap), exactly like the layer Eraser.
     * o: { x, y (fractional ok), radius, hardness, cap 0..1, erase:true, footprint, sel?, selW }
     */
    function maskDab(mask, W, H, key, o) {
        const s = getSession(key, W, H);
        const r = Math.max(0.5, +o.radius || 1);
        const cx = (+o.x) + 0.5, cy = (+o.y) + 0.5;
        const x0 = Math.max(0, Math.floor(cx - r - 1)), y0 = Math.max(0, Math.floor(cy - r - 1));
        const x1 = Math.min(W, Math.ceil(cx + r + 1)), y1 = Math.min(H, Math.ceil(cy + r + 1));
        if (x1 <= x0 || y1 <= y0) return null;
        const hardness = o.hardness == null ? 1 : o.hardness;
        const cap = Math.max(0, Math.min(1, o.cap == null ? 1 : o.cap));
        const fp = o.footprint && o.footprint.shape !== 'round' ? o.footprint : null;
        const cov = s.cov, orig = s.orig;
        let touched = false;
        for (let y = y0; y < y1; y++) {
            const dy = y + 0.5 - cy;
            for (let x = x0; x < x1; x++) {
                const dx = x + 0.5 - cx;
                let v;
                if (fp) {
                    const ix = x - Math.round(o.x), iy = y - Math.round(o.y);
                    if (!fp.contains(ix, iy, ix * ix + iy * iy)) continue;
                    v = softFall(fp.distanceSquared(ix, iy), r, hardness);
                } else {
                    const d2 = dx * dx + dy * dy;
                    if (d2 >= (r + 0.5) * (r + 0.5)) continue;
                    v = dabCoverage(Math.sqrt(d2), r, hardness);
                }
                if (v <= 0) continue;
                const gi = y * W + x, c = cov[gi], nv = c + v * (1 - c);
                if (!(nv > c)) continue;
                if (c === 0) orig[gi * 4] = mask[gi];
                cov[gi] = nv;
                mask[gi] = o.erase ? Math.round(orig[gi * 4] * (1 - nv * cap)) : Math.round(orig[gi * 4] + (255 - orig[gi * 4]) * nv * cap);
                touched = true;
            }
        }
        if (!touched) return null;
        growDirty(s, x0, y0, x1, y1);
        s.dabs++;
        return { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
    }

    return Object.freeze({
        enabled, dabCoverage, paintDab, paintDabData, retouchDab, smudgeState, smudgeDab, maskDab, endSession, toneCurve, dodgeBurn, localBlur, luma,
        _session: () => session,
    });
});
