/* Algorithm ported from PhotoCraft crates/algo/src/transform.rs (warp_surface, Homography, Catmull-Rom)
   and crates/algo/src/resample.rs (taps / resize_surface pre-reduction).
   (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0 (elected: MIT) - see THIRD_PARTY_NOTICES.md.
   Modified: rewritten in JavaScript for SPB (typed arrays, single thread, canvas bridge).
   SPB lane PORT-W3 (transform), 2026-10-09. Owner verdict: "Our tools basically SUCK" (2026-10-09).

   SPBPcWarp = projective (homography) warp with premultiplied-alpha sampling (nearest / bilinear /
   Catmull-Rom bicubic) and proper pre-filtering of large reductions (no aliasing, no dark fringes).
   Kill switch: window.SPB_PC_W3_OFF = true  -> every SPB hook falls back to the old drawImage path. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcWarp = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // ---- 3x3 homography helpers (row-major, [x',y',w'] = H [x,y,1]) -------------------------
    const IDENTITY = [1, 0, 0, 0, 1, 0, 0, 0, 1];
    function hApply(m, x, y) {
        const w = m[6] * x + m[7] * y + m[8];
        return [(m[0] * x + m[1] * y + m[2]) / w, (m[3] * x + m[4] * y + m[5]) / w];
    }
    function hMul(a, b) {
        const r = new Array(9);
        for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
            r[i * 3 + j] = a[i * 3] * b[j] + a[i * 3 + 1] * b[3 + j] + a[i * 3 + 2] * b[6 + j];
        }
        return r;
    }
    function hInverse(m) {
        const c = [
            m[4] * m[8] - m[5] * m[7], m[2] * m[7] - m[1] * m[8], m[1] * m[5] - m[2] * m[4],
            m[5] * m[6] - m[3] * m[8], m[0] * m[8] - m[2] * m[6], m[2] * m[3] - m[0] * m[5],
            m[3] * m[7] - m[4] * m[6], m[1] * m[6] - m[0] * m[7], m[0] * m[4] - m[1] * m[3],
        ];
        const det = m[0] * c[0] + m[1] * c[3] + m[2] * c[6];
        if (Math.abs(det) < 1e-12) return null;
        return c.map(function (v) { return v / det; });
    }
    function squareToQuad(q) {
        const x0 = q[0][0], y0 = q[0][1], x1 = q[1][0], y1 = q[1][1], x2 = q[2][0], y2 = q[2][1], x3 = q[3][0], y3 = q[3][1];
        const sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
        if (Math.abs(sx) < 1e-12 && Math.abs(sy) < 1e-12) return [x1 - x0, x3 - x0, x0, y1 - y0, y3 - y0, y0, 0, 0, 1];
        const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
        const den = dx1 * dy2 - dx2 * dy1;
        if (Math.abs(den) < 1e-12) return null;
        const g = (sx * dy2 - dx2 * sy) / den, h = (dx1 * sy - sx * dy1) / den;
        return [x1 - x0 + g * x1, x3 - x0 + h * x3, x0, y1 - y0 + g * y1, y3 - y0 + h * y3, y0, g, h, 1];
    }
    // rect [x0,y0,x1,y1] -> quad (tl,tr,br,bl)
    function rectToQuad(r, quad) {
        const w = r[2] - r[0], h = r[3] - r[1];
        if (!(w > 0) || !(h > 0)) return null;
        const q = squareToQuad(quad);
        if (!q) return null;
        return hMul(q, [1 / w, 0, -r[0] / w, 0, 1 / h, -r[1] / h, 0, 0, 1]);
    }
    function localScale(m, x, y) {
        const e = 0.5, a = hApply(m, x - e, y), b = hApply(m, x + e, y), c = hApply(m, x, y - e), d = hApply(m, x, y + e);
        const jx0 = b[0] - a[0], jx1 = b[1] - a[1], jy0 = d[0] - c[0], jy1 = d[1] - c[1];
        return Math.sqrt(Math.abs(jx0 * jy1 - jx1 * jy0));
    }

    // ---- Catmull-Rom ----------------------------------------------------------------------
    function crWeight(x) { // Keys cubic a=-0.5 (resample.rs Bicubic)
        x = Math.abs(x);
        if (x < 1) return 1.5 * x * x * x - 2.5 * x * x + 1;
        if (x < 2) return -0.5 * x * x * x + 2.5 * x * x - 4 * x + 2;
        return 0;
    }

    // ---- premultiply / pre-reduction ---------------------------------------------------------
    // Crop (x0,y0,x1,y1) of straight RGBA8 -> premultiplied Float32 (0..1), 4 channels.
    function premultCrop(rgba, sw, rect) {
        const w = rect.x1 - rect.x0, h = rect.y1 - rect.y0;
        const out = new Float32Array(w * h * 4);
        const k = 1 / 255;
        for (let y = 0; y < h; y++) {
            let si = ((rect.y0 + y) * sw + rect.x0) * 4, oi = y * w * 4;
            for (let x = 0; x < w; x++, si += 4, oi += 4) {
                const a = rgba[si + 3] * k;
                out[oi] = rgba[si] * k * a; out[oi + 1] = rgba[si + 1] * k * a;
                out[oi + 2] = rgba[si + 2] * k * a; out[oi + 3] = a;
            }
        }
        return { data: out, width: w, height: h };
    }
    // Separable Catmull-Rom resize of a premultiplied surface by factor f (<1), taps() in resample.rs:
    // u = (o+0.5)/f-0.5, support 2/f, weights normalized, outside the surface reads transparent.
    function resizeAxis(src, sw, sh, f, horizontal) {
        const inN = horizontal ? sw : sh, outN = Math.max(1, Math.round(inN * f));
        const stretch = 1 / f, support = 2 * stretch;
        const ow = horizontal ? outN : sw, oh = horizontal ? sh : outN;
        const out = new Float32Array(ow * oh * 4);
        const taps = [];
        for (let o = 0; o < outN; o++) {
            const u = (o + 0.5) / f - 0.5, lo = Math.ceil(u - support), hi = Math.floor(u + support);
            const w = [];
            let s = 0;
            for (let i = lo; i <= hi; i++) { const v = crWeight((i - u) / stretch); w.push(v); s += v; }
            if (Math.abs(s) > 1e-12) for (let i = 0; i < w.length; i++) w[i] /= s;
            // keep only taps inside the surface (outside is transparent -> contributes 0)
            const a = Math.max(lo, 0), b = Math.min(hi, inN - 1);
            taps.push({ start: a, w: a > b ? [] : w.slice(a - lo, b - lo + 1) });
        }
        if (horizontal) {
            for (let y = 0; y < sh; y++) for (let o = 0; o < outN; o++) {
                const t = taps[o], n = t.w.length;
                let r = 0, g = 0, b = 0, a = 0, si = (y * sw + t.start) * 4;
                for (let k = 0; k < n; k++, si += 4) { const wk = t.w[k]; r += src[si] * wk; g += src[si + 1] * wk; b += src[si + 2] * wk; a += src[si + 3] * wk; }
                const oi = (y * outN + o) * 4; out[oi] = r; out[oi + 1] = g; out[oi + 2] = b; out[oi + 3] = a;
            }
        } else {
            for (let o = 0; o < outN; o++) {
                const t = taps[o], n = t.w.length;
                for (let x = 0; x < sw; x++) {
                    let r = 0, g = 0, b = 0, a = 0, si = (t.start * sw + x) * 4;
                    for (let k = 0; k < n; k++, si += sw * 4) { const wk = t.w[k]; r += src[si] * wk; g += src[si + 1] * wk; b += src[si + 2] * wk; a += src[si + 3] * wk; }
                    const oi = (o * sw + x) * 4; out[oi] = r; out[oi + 1] = g; out[oi + 2] = b; out[oi + 3] = a;
                }
            }
        }
        return { data: out, width: ow, height: oh };
    }
    function reducePremult(s, f) {
        const hz = resizeAxis(s.data, s.width, s.height, f, true);
        return resizeAxis(hz.data, hz.width, hz.height, f, false);
    }

    // ---- core warp ---------------------------------------------------------------------------
    // src: { data: Uint8ClampedArray|Uint8Array straight RGBA, width, height }  OR  { premult: {data,width,height}, ...}
    // rect: {x0,y0,x1,y1} content rectangle inside src; H: source px -> destination px (9 numbers).
    // returns { x, y, width, height, data (straight RGBA8) } or null when empty.
    function warp(src, rect, H, interp, opts) {
        interp = interp || 'bicubic';
        opts = opts || {};
        if (!src || !(rect.x1 > rect.x0) || !(rect.y1 > rect.y0)) return null;
        const t0 = typeof performance !== 'undefined' ? performance.now() : 0;
        let pm = src.premultCache && src.premultCache.get(rect.x0 + ',' + rect.y0 + ',' + rect.x1 + ',' + rect.y1);
        if (!pm) {
            pm = premultCrop(src.data, src.width, rect);
            if (src.premultCache) src.premultCache.set(rect.x0 + ',' + rect.y0 + ',' + rect.x1 + ',' + rect.y1, pm);
        }
        // local coords: source px (x,y) -> crop px (x-x0,y-y0)
        let h = hMul(H, [1, 0, rect.x0, 0, 1, rect.y0, 0, 0, 1]);
        let sw = pm.width, sh = pm.height, data = pm.data;
        const cx = sw / 2, cy = sh / 2;
        const scale = localScale(h, cx, cy);
        if (interp !== 'nearest' && scale < 0.5 && scale > 0) {
            const f = Math.min(1, Math.pow(2, Math.ceil(Math.log2(scale)))); // remaining scale in [0.5,1)
            const key = 'r' + f + ':' + rect.x0 + ',' + rect.y0 + ',' + rect.x1 + ',' + rect.y1;
            let red = src.premultCache && src.premultCache.get(key);
            if (!red) { red = reducePremult(pm, f); if (src.premultCache) src.premultCache.set(key, red); }
            data = red.data;
            h = hMul(h, [1 / f, 0, 0, 0, 1 / f, 0, 0, 0, 1]);
            // the reduced surface has round(sw*f) pixels; correct the tiny rounding scale
            sw = red.width; sh = red.height;
        }
        const inv = hInverse(h);
        if (!inv) return null;
        const corners = [hApply(h, 0, 0), hApply(h, sw, 0), hApply(h, sw, sh), hApply(h, 0, sh)];
        for (let i = 0; i < 4; i++) if (!isFinite(corners[i][0]) || !isFinite(corners[i][1])) return null;
        const lim = 1 << 20;
        let bx0 = Math.floor(Math.max(Math.min(corners[0][0], corners[1][0], corners[2][0], corners[3][0]), -lim)) - 1;
        let by0 = Math.floor(Math.max(Math.min(corners[0][1], corners[1][1], corners[2][1], corners[3][1]), -lim)) - 1;
        let bx1 = Math.ceil(Math.min(Math.max(corners[0][0], corners[1][0], corners[2][0], corners[3][0]), lim)) + 1;
        let by1 = Math.ceil(Math.min(Math.max(corners[0][1], corners[1][1], corners[2][1], corners[3][1]), lim)) + 1;
        if (opts.clip) { bx0 = Math.max(bx0, opts.clip.x0); by0 = Math.max(by0, opts.clip.y0); bx1 = Math.min(bx1, opts.clip.x1); by1 = Math.min(by1, opts.clip.y1); }
        const dw = bx1 - bx0, dh = by1 - by0;
        if (dw <= 0 || dh <= 0 || dw * dh > 80e6) return null;
        const out = new Uint8ClampedArray(dw * dh * 4);
        const m = inv;
        const affine = Math.abs(m[6]) < 1e-14 && Math.abs(m[7]) < 1e-14 && Math.abs(m[8] - 1) < 1e-12;
        const U0 = -1, V0 = -1, U1 = sw, V1 = sh; // u,v window (pixel-center coords) as in warp_surface
        const swm = sw, shm = sh;
        const row = swm * 4;
        let any = false;
        const wxA = new Float64Array(4), wyA = new Float64Array(4);
        for (let y = 0; y < dh; y++) {
            const py = by0 + y + 0.5;
            for (let x = 0; x < dw; x++) {
                const px = bx0 + x + 0.5;
                let u, v;
                if (affine) { u = m[0] * px + m[1] * py + m[2]; v = m[3] * px + m[4] * py + m[5]; }
                else { const w = m[6] * px + m[7] * py + m[8]; u = (m[0] * px + m[1] * py + m[2]) / w; v = (m[3] * px + m[4] * py + m[5]) / w; }
                u -= 0.5; v -= 0.5;
                // snap away float noise so integer-aligned maps stay exact
                const ru = Math.round(u), rv = Math.round(v);
                if (Math.abs(u - ru) < 1e-7) u = ru;
                if (Math.abs(v - rv) < 1e-7) v = rv;
                if (u < U0 || v < V0 || u > U1 || v > V1) continue;
                let r = 0, g = 0, b = 0, a = 0;
                if (interp === 'nearest') {
                    const ix = Math.floor(u + 0.5), iy = Math.floor(v + 0.5);
                    if (ix < 0 || iy < 0 || ix >= swm || iy >= shm) continue;
                    const si = iy * row + ix * 4; r = data[si]; g = data[si + 1]; b = data[si + 2]; a = data[si + 3];
                } else if (interp === 'bilinear') {
                    const ix = Math.floor(u), iy = Math.floor(v), fx = u - ix, fy = v - iy;
                    for (let j = 0; j < 2; j++) {
                        const yy = iy + j; if (yy < 0 || yy >= shm) continue;
                        const wy = j ? fy : 1 - fy;
                        for (let i = 0; i < 2; i++) {
                            const xx = ix + i; if (xx < 0 || xx >= swm) continue;
                            const wk = (i ? fx : 1 - fx) * wy, si = yy * row + xx * 4;
                            r += data[si] * wk; g += data[si + 1] * wk; b += data[si + 2] * wk; a += data[si + 3] * wk;
                        }
                    }
                } else {
                    const ix = Math.floor(u), iy = Math.floor(v), tx = u - ix, ty = v - iy;
                    const tx2 = tx * tx, tx3 = tx2 * tx, ty2 = ty * ty, ty3 = ty2 * ty;
                    wxA[0] = -0.5 * tx3 + tx2 - 0.5 * tx; wxA[1] = 1.5 * tx3 - 2.5 * tx2 + 1; wxA[2] = -1.5 * tx3 + 2 * tx2 + 0.5 * tx; wxA[3] = 0.5 * tx3 - 0.5 * tx2;
                    wyA[0] = -0.5 * ty3 + ty2 - 0.5 * ty; wyA[1] = 1.5 * ty3 - 2.5 * ty2 + 1; wyA[2] = -1.5 * ty3 + 2 * ty2 + 0.5 * ty; wyA[3] = 0.5 * ty3 - 0.5 * ty2;
                    if (ix >= 1 && iy >= 1 && ix + 2 < swm && iy + 2 < shm) {
                        // interior fast path: unrolled 4x4 Catmull-Rom on premultiplied floats
                        const x0 = wxA[0], x1 = wxA[1], x2 = wxA[2], x3 = wxA[3];
                        let si = (iy - 1) * row + (ix - 1) * 4;
                        for (let j = 0; j < 4; j++, si += row) {
                            const wy = wyA[j];
                            const k0 = x0 * wy, k1 = x1 * wy, k2 = x2 * wy, k3 = x3 * wy;
                            r += data[si] * k0 + data[si + 4] * k1 + data[si + 8] * k2 + data[si + 12] * k3;
                            g += data[si + 1] * k0 + data[si + 5] * k1 + data[si + 9] * k2 + data[si + 13] * k3;
                            b += data[si + 2] * k0 + data[si + 6] * k1 + data[si + 10] * k2 + data[si + 14] * k3;
                            a += data[si + 3] * k0 + data[si + 7] * k1 + data[si + 11] * k2 + data[si + 15] * k3;
                        }
                    } else {
                        for (let j = 0; j < 4; j++) {
                            const yy = iy - 1 + j, wy = wyA[j];
                            if (wy === 0 || yy < 0 || yy >= shm) continue;
                            for (let i = 0; i < 4; i++) {
                                const wx = wxA[i], xx = ix - 1 + i;
                                if (wx === 0 || xx < 0 || xx >= swm) continue;
                                const wk = wx * wy, si = yy * row + xx * 4;
                                r += data[si] * wk; g += data[si + 1] * wk; b += data[si + 2] * wk; a += data[si + 3] * wk;
                            }
                        }
                    }
                }
                if (a > 1) a = 1;
                if (a <= 0) continue;
                any = true;
                const oi = (y * dw + x) * 4, inva = 255 / a;
                let cr = r * inva, cg = g * inva, cb = b * inva;
                out[oi] = cr > 255 ? 255 : cr < 0 ? 0 : Math.floor(cr + 0.5);
                out[oi + 1] = cg > 255 ? 255 : cg < 0 ? 0 : Math.floor(cg + 0.5);
                out[oi + 2] = cb > 255 ? 255 : cb < 0 ? 0 : Math.floor(cb + 0.5);
                out[oi + 3] = Math.floor(a * 255 + 0.5);
            }
        }
        if (!any) return null;
        return { x: bx0, y: by0, width: dw, height: dh, data: out,
            ms: (typeof performance !== 'undefined' ? performance.now() : 0) - t0 };
    }

    // ---- state -> homography -----------------------------------------------------------------
    // Matches the old canvas order: ctx.translate(center); ctx.scale(flip); ctx.rotate(rot); drawImage(box centred).
    function matrixFromState(state, sw, sh) {
        const w = Math.max(1, Math.abs(Number(state.boxW) || 0)), h = Math.max(1, Math.abs(Number(state.boxH) || 0));
        if (state.quad && state.quad.length === 4) {
            return rectToQuad([0, 0, sw, sh], state.quad);
        }
        const fx = (Number(state.scaleX) || 1) < 0 ? -1 : 1, fy = (Number(state.scaleY) || 1) < 0 ? -1 : 1;
        const rad = (Number(state.rotation) || 0) * Math.PI / 180;
        let c = Math.cos(rad), s = Math.sin(rad);
        // exact quarter turns: avoid cos(90deg)=6e-17 noise
        const q = Math.round((Number(state.rotation) || 0) / 90);
        if (Math.abs((Number(state.rotation) || 0) - q * 90) < 1e-9) { const k = ((q % 4) + 4) % 4; c = [1, 0, -1, 0][k]; s = [0, 1, 0, -1][k]; }
        // p_dest = C + F * R * S * (p - (sw/2, sh/2)), S = diag(w/sw, h/sh)
        const a = c * (w / sw), b = -s * (h / sh), cc = s * (w / sw), d = c * (h / sh); // R*S
        const m00 = fx * a, m01 = fx * b, m10 = fy * cc, m11 = fy * d;
        const tx = Number(state.centerX) - (m00 * sw / 2 + m01 * sh / 2);
        const ty = Number(state.centerY) - (m10 * sw / 2 + m11 * sh / 2);
        return [m00, m01, tx, m10, m11, ty, 0, 0, 1];
    }

    // ---- canvas bridge ---------------------------------------------------------------------------
    // Drop-in for ctx.drawImage(source, sx,sy,sw,sh, dx,dy,dw,dh) under the ctx's CURRENT transform, using
    // the PhotoCraft warp instead of the browser resampler. Returns true when drawn (or nothing to draw);
    // false = caller must use the old path (flag off, no DOM, CPU-only fallback over its size budget).
    // Two backends, SAME maths: a WebGL2 fragment shader (Catmull-Rom 4x4 over premultiplied texels, mip-level
    // pre-reduction, ~ms at 2048^2: used for live preview AND Apply so preview == result) and the CPU engine
    // `warp()` above (reference, used when WebGL2 is unavailable or window.SPB_PC_W3_GPU_OFF).
    let cache = null, scratch = null, GL = undefined;
    const CACHE_MS = 700;
    function now() { return typeof performance !== 'undefined' ? performance.now() : Date.now(); }
    function disabled() { return typeof window !== 'undefined' && !!window.SPB_PC_W3_OFF; }
    function invalidate() { cache = null; if (GL) GL.src = null; }
    function pixelsOf(source) {
        const w = source.naturalWidth || source.width, h = source.naturalHeight || source.height;
        if (!(w > 0) || !(h > 0)) return null;
        const t = now();
        if (cache && cache.source === source && cache.w === w && cache.h === h && t - cache.t < CACHE_MS) { cache.t = t; return cache.px; }
        let cv = source;
        if (!(typeof HTMLCanvasElement !== 'undefined' && source instanceof HTMLCanvasElement)) {
            cv = document.createElement('canvas'); cv.width = w; cv.height = h;
            cv.getContext('2d', { willReadFrequently: true }).drawImage(source, 0, 0);
        }
        const id = cv.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, w, h);
        const px = { data: id.data, width: w, height: h, premultCache: new Map() };
        cache = { source: source, w: w, h: h, t: t, px: px };
        return px;
    }

    // ---- WebGL2 backend ----
    const VS = '#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}';
    const FS = '#version 300 es\nprecision highp float;precision highp int;\n' +
        'uniform sampler2D uTex;uniform mat3 uInv;uniform vec4 uRect;uniform vec2 uOrg;uniform float uH;uniform int uLod;uniform int uMode;out vec4 o;\n' +
        'vec4 fetchT(ivec2 c){ if(c.x<int(uRect.x)||c.y<int(uRect.y)||c.x>=int(uRect.z)||c.y>=int(uRect.w)) return vec4(0.0); return texelFetch(uTex,c,uLod);}\n' +
        'vec4 cr(float t){float t2=t*t,t3=t2*t;return vec4(-0.5*t3+t2-0.5*t,1.5*t3-2.5*t2+1.0,-1.5*t3+2.0*t2+0.5*t,0.5*t3-0.5*t2);}\n' +
        'void main(){vec3 q=uInv*vec3(gl_FragCoord.x+uOrg.x,(uH-gl_FragCoord.y)+uOrg.y,1.0);vec2 uv=q.xy/q.z-0.5;\n' +
        ' vec2 r=floor(uv+0.5);if(abs(uv.x-r.x)<1e-4)uv.x=r.x;if(abs(uv.y-r.y)<1e-4)uv.y=r.y;\n' +
        ' if(uv.x<uRect.x-1.0||uv.y<uRect.y-1.0||uv.x>uRect.z||uv.y>uRect.w){o=vec4(0.0);return;}\n' +
        ' vec2 f=floor(uv);ivec2 i0=ivec2(f);vec2 t=uv-f;vec4 acc=vec4(0.0);\n' +
        ' if(uMode==0){vec4 wx=cr(t.x),wy=cr(t.y);for(int j=0;j<4;j++){for(int i=0;i<4;i++){acc+=fetchT(i0+ivec2(i-1,j-1))*(wx[i]*wy[j]);}}}\n' +
        ' else if(uMode==1){acc=fetchT(i0)*((1.0-t.x)*(1.0-t.y))+fetchT(i0+ivec2(1,0))*(t.x*(1.0-t.y))+fetchT(i0+ivec2(0,1))*((1.0-t.x)*t.y)+fetchT(i0+ivec2(1,1))*(t.x*t.y);}\n' +
        ' else {acc=fetchT(ivec2(floor(uv+0.5)));}\n' +
        ' acc.a=clamp(acc.a,0.0,1.0);acc.rgb=clamp(acc.rgb,0.0,acc.a);o=acc;}';
    function glInit() {
        if (GL !== undefined) return GL;
        GL = null;
        try {
            if (typeof document === 'undefined' || (typeof window !== 'undefined' && window.SPB_PC_W3_GPU_OFF)) return GL;
            const c = document.createElement('canvas'); c.width = 16; c.height = 16;
            const gl = c.getContext('webgl2', { premultipliedAlpha: true, alpha: true, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: false });
            if (!gl) return GL;
            const sh = function (type, src) { const s2 = gl.createShader(type); gl.shaderSource(s2, src); gl.compileShader(s2); if (!gl.getShaderParameter(s2, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s2)); return s2; };
            const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
            if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
            const loc = {}; ['uTex', 'uInv', 'uRect', 'uOrg', 'uH', 'uLod', 'uMode'].forEach(function (n) { loc[n] = gl.getUniformLocation(pr, n); });
            GL = { gl: gl, c: c, pr: pr, loc: loc, tex: gl.createTexture(), src: null, w: 0, h: 0, t: 0, mips: false, max: Math.min(gl.getParameter(gl.MAX_RENDERBUFFER_SIZE), 8192) };
            c.addEventListener('webglcontextlost', function (e) { e.preventDefault(); GL = null; }, false);
        } catch (err) { GL = null; if (typeof console !== 'undefined') console.warn('[pc-warp] WebGL2 backend unavailable:', err && err.message); }
        return GL;
    }
    function glSource(source, w, h, needMips) {
        const g = GL, gl = g.gl, t = now();
        if (!(g.src === source && g.w === w && g.h === h && t - g.t < CACHE_MS)) {
            gl.bindTexture(gl.TEXTURE_2D, g.tex);
            gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, source);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            g.src = source; g.w = w; g.h = h; g.mips = false;
        }
        g.t = t;
        if (needMips && !g.mips) {
            gl.bindTexture(gl.TEXTURE_2D, g.tex);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST_MIPMAP_NEAREST);
            gl.generateMipmap(gl.TEXTURE_2D); g.mips = true;
        }
    }
    // Render src -> device region reg under H (source px -> device px) and draw it on ctx. false = unsupported.
    function glBlit(ctx, source, sw0, sh0, rect, H, reg, interp) {
        const g = glInit();
        if (!g) return false;
        const w = reg.x1 - reg.x0, h = reg.y1 - reg.y0;
        if (w > g.max || h > g.max) return false;
        const inv = hInverse(H);
        if (!inv) return true;
        const full = rect.x0 === 0 && rect.y0 === 0 && rect.x1 === sw0 && rect.y1 === sh0;
        let L = 0;
        if (interp !== 'nearest') {
            const sc = localScale(H, (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2);
            if (sc > 0 && sc < 0.5) L = Math.max(0, Math.min(10, Math.floor(-Math.log2(sc))));
        }
        if (L > 0 && !full) L = 0; // never mip-bleed a sub-rect crop into its siblings
        const gl = g.gl;
        glSource(source, sw0, sh0, L > 0);
        // inverse maps device px -> source px; scale x/y rows to level-L texel coords. GLSL mat3 is column-major.
        const k = 1 / Math.pow(2, L);
        const m = [inv[0] * k, inv[3] * k, inv[6], inv[1] * k, inv[4] * k, inv[7], inv[2] * k, inv[5] * k, inv[8]];
        if (g.c.width < w || g.c.height < h) { g.c.width = Math.max(g.c.width, w); g.c.height = Math.max(g.c.height, h); }
        gl.viewport(0, 0, w, h);
        gl.disable(gl.BLEND); gl.disable(gl.DEPTH_TEST);
        gl.useProgram(g.pr);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, g.tex);
        gl.uniform1i(g.loc.uTex, 0);
        gl.uniformMatrix3fv(g.loc.uInv, false, new Float32Array(m));
        gl.uniform4f(g.loc.uRect, Math.floor(rect.x0 * k), Math.floor(rect.y0 * k), Math.ceil(rect.x1 * k), Math.ceil(rect.y1 * k));
        gl.uniform2f(g.loc.uOrg, reg.x0, reg.y0);
        gl.uniform1f(g.loc.uH, h);
        gl.uniform1i(g.loc.uLod, L);
        gl.uniform1i(g.loc.uMode, interp === 'nearest' ? 2 : interp === 'bilinear' ? 1 : 0);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(g.c, 0, g.c.height - h, w, h, reg.x0, reg.y0, w, h);
        ctx.restore();
        return true;
    }
    function deviceRegion(H, rect, cw, ch) {
        const xs = [], ys = [];
        [[rect.x0, rect.y0], [rect.x1, rect.y0], [rect.x1, rect.y1], [rect.x0, rect.y1]].forEach(function (p) { const q = hApply(H, p[0], p[1]); xs.push(q[0]); ys.push(q[1]); });
        for (let i = 0; i < 4; i++) if (!isFinite(xs[i]) || !isFinite(ys[i])) return null;
        const x0 = Math.max(0, Math.floor(Math.min.apply(null, xs)) - 1), y0 = Math.max(0, Math.floor(Math.min.apply(null, ys)) - 1);
        const x1 = Math.min(cw, Math.ceil(Math.max.apply(null, xs)) + 1), y1 = Math.min(ch, Math.ceil(Math.max.apply(null, ys)) + 1);
        return (x1 > x0 && y1 > y0) ? { x0: x0, y0: y0, x1: x1, y1: y1 } : null;
    }
    function interpName(opts) { return (opts && opts.interp) || (typeof window !== 'undefined' && window.SPB_PC_W3_INTERP) || 'bicubic'; }
    // Common back end: H maps source px -> ctx device px.
    function blit(ctx, source, rect, H, opts) {
        const sw0 = source.naturalWidth || source.width, sh0 = source.naturalHeight || source.height;
        const cw = ctx.canvas.width, ch = ctx.canvas.height;
        const reg = deviceRegion(H, rect, cw, ch);
        if (!reg) return true; // nothing visible
        const interp = interpName(opts);
        if (!(typeof window !== 'undefined' && window.SPB_PC_W3_GPU_OFF) && glBlit(ctx, source, sw0, sh0, rect, H, reg, interp)) return true;
        // CPU reference path (bounded for interactive use unless exact)
        if ((reg.x1 - reg.x0) * (reg.y1 - reg.y0) > ((opts && opts.maxPx) || Infinity)) return false;
        const px = pixelsOf(source);
        if (!px) return false;
        const res = warp(px, rect, H, interp, { clip: { x0: 0, y0: 0, x1: cw, y1: ch } });
        if (!res) return true;
        if (!scratch) scratch = document.createElement('canvas');
        if (scratch.width !== res.width) scratch.width = res.width;
        if (scratch.height !== res.height) scratch.height = res.height;
        scratch.getContext('2d').putImageData(new ImageData(res.data, res.width, res.height), 0, 0);
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingEnabled = false;
        ctx.drawImage(scratch, res.x, res.y);
        ctx.restore();
        return true;
    }
    function drawImage(ctx, source, sx, sy, sw, sh, dx, dy, dw, dh, opts) {
        if (disabled() || !ctx || !source || typeof document === 'undefined' || typeof ctx.getTransform !== 'function') return false;
        if (!(sw > 0) || !(sh > 0) || !isFinite(dx + dy + dw + dh) || dw === 0 || dh === 0) return false;
        const T = ctx.getTransform();
        const toDev = [T.a, T.c, T.e, T.b, T.d, T.f, 0, 0, 1];
        const H = hMul(toDev, hMul([dw / sw, 0, dx, 0, dh / sh, dy, 0, 0, 1], [1, 0, -sx, 0, 1, -sy, 0, 0, 1]));
        const iw = source.naturalWidth || source.width, ih = source.naturalHeight || source.height;
        const rect = { x0: Math.max(0, Math.floor(sx)), y0: Math.max(0, Math.floor(sy)), x1: Math.min(iw, Math.ceil(sx + sw)), y1: Math.min(ih, Math.ceil(sy + sh)) };
        if (!(rect.x1 > rect.x0) || !(rect.y1 > rect.y0)) return true;
        return blit(ctx, source, rect, H, opts);
    }
    // Four-corner (distort / perspective / skew) draw: source rect -> quad (tl,tr,br,bl) in ctx space.
    function drawQuad(ctx, source, sx, sy, sw, sh, quad, opts) {
        if (disabled() || !ctx || !source || !quad || quad.length !== 4 || typeof ctx.getTransform !== 'function') return false;
        const T = ctx.getTransform();
        const q = quad.map(function (p) { return [T.a * p[0] + T.c * p[1] + T.e, T.b * p[0] + T.d * p[1] + T.f]; });
        const Hq = rectToQuad([sx, sy, sx + sw, sy + sh], q);
        if (!Hq) return false;
        const iw = source.naturalWidth || source.width, ih = source.naturalHeight || source.height;
        const rect = { x0: Math.max(0, Math.floor(sx)), y0: Math.max(0, Math.floor(sy)), x1: Math.min(iw, Math.ceil(sx + sw)), y1: Math.min(ih, Math.ceil(sy + sh)) };
        return blit(ctx, source, rect, Hq, Object.assign({ maxPx: Infinity }, opts || {}));
    }

    // Bake a source canvas/image through a 4-corner quad (tl,tr,br,bl in DOCUMENT coords): skew / distort /
    // perspective all reduce to this. Returns { canvas, bbox:[x1,y1,x2,y2] } sized to the quad's AABB
    // (a one-pixel AA margin), or null. The caller owns undo + layer assignment.
    function bakeQuad(source, quad, opts) {
        if (disabled() || !source || !quad || quad.length !== 4 || typeof document === 'undefined') return null;
        const sw = source.naturalWidth || source.width, sh = source.naturalHeight || source.height;
        const xs = quad.map(function (p) { return p[0]; }), ys = quad.map(function (p) { return p[1]; });
        const x1 = Math.floor(Math.min.apply(null, xs)) - 1, y1 = Math.floor(Math.min.apply(null, ys)) - 1;
        const x2 = Math.ceil(Math.max.apply(null, xs)) + 1, y2 = Math.ceil(Math.max.apply(null, ys)) + 1;
        const w = x2 - x1, h = y2 - y1;
        if (!(w > 0) || !(h > 0) || w * h > 64e6) return null;
        const out = document.createElement('canvas'); out.width = w; out.height = h;
        const ctx = out.getContext('2d', { willReadFrequently: true });
        const local = quad.map(function (p) { return [p[0] - x1, p[1] - y1]; });
        invalidate();
        if (!drawQuad(ctx, source, 0, 0, sw, sh, local, opts)) return null;
        // TOOLS-FIX 2026-10-09 (QA defect 5): canvas stores premultiplied 8-bit, so alpha 1-4 pixels read back with quantised dark
        // straight RGB. Clear them (<=4/255 = invisible) so no later alpha boost can show them. Skipped for the cheap drag preview.
        if (!(opts && opts.interp)) {
            try {
                const id = ctx.getImageData(0, 0, w, h), d = id.data, bad = [];
                for (let i = 3; i < d.length; i += 4) { const al = d[i]; if (al !== 0 && al <= 4) bad.push((i - 3) >> 2); }
                if (bad.length && bad.length < 200000) { for (let k = 0; k < bad.length; k++) ctx.clearRect(bad[k] % w, (bad[k] / w) | 0, 1, 1); }
            } catch (_e) { /* tainted or unavailable: leave as baked */ }
        }
        return { canvas: out, bbox: [x1, y1, x2, y2] };
    }

    return { bakeQuad, drawImage, drawQuad, invalidate, pixelsOf, liveBudgetPx: 900000, glReady: function () { return !!glInit(); }, IDENTITY, hApply, hMul, hInverse, rectToQuad, localScale, crWeight, premultCrop, reducePremult, warp, matrixFromState, _version: 1 };
});
